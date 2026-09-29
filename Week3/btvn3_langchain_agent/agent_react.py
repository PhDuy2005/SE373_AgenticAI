# -*- coding: utf-8 -*-
"""BTVN#3 · Mẫu Thiết Kế 1: Agent ReAct (Reasoning + Acting).

Cơ chế hoạt động (Slide 18-20 Buổi 03):
    Vòng lặp xen kẽ liên tục: Thought -> Action -> Observation -> Thought...
    Mỗi bước suy luận được nuôi dưỡng bởi kết quả thực tế từ môi trường thay vì
    chỉ dựa vào suy đoán tĩnh của mô hình.

Được bảo vệ bởi 4 Lớp Harness:
    - Lớp 1: Ràng buộc là dữ liệu (FlightConstraints)
    - Lớp 2: Tiêu chí hoàn thành kiểm bằng code (check_completion Sensor)
    - Lớp 3: Kiểm quyền trước khi gọi tool (PreExecutionAuthHook)
    - Lớp 4: Bàn giao có cấu trúc khi dừng (ban_giao)
    - Cơ chế phụ trợ: LoopDetector & BudgetManager
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from mock_flight_tools import (
    search_flights,
    check_seat,
    book_seat,
    pay,
    get_booking,
    reset_flight_database,
)
from flight_harness import (
    FlightConstraints,
    check_completion,
    PreExecutionAuthHook,
    ban_giao,
    LoopDetector,
    BudgetManager,
)
from model_provider import MockBookingModel, HumanMessage, AIMessage, ToolMessage


TOOL_MAP = {
    "search_flights": search_flights,
    "check_seat": check_seat,
    "book_seat": book_seat,
    "pay": pay,
    "get_booking": get_booking,
}


def run_react_agent(
    user_query: str,
    constraints: Optional[FlightConstraints] = None,
    scenario: int = 1,
    custom_model: Optional[Any] = None,
    max_steps: int = 10,
    verbose: bool = False
) -> Dict[str, Any]:
    """Khởi chạy chu trình ReAct Agent đặt vé máy bay tích hợp 4 lớp harness."""
    start_time = time.time()
    cons = constraints or FlightConstraints()

    # 1. Khởi tạo Harness & Middleware an toàn
    auth_hook = PreExecutionAuthHook(cons)
    loop_detector = LoopDetector(window=6, repeat_k=2, same_obs_k=3, stall_n=3)
    budget = BudgetManager(max_steps=max_steps, max_tokens=15_000)

    # 2. Khởi tạo Model
    model = custom_model or MockBookingModel(pattern="react", scenario=scenario)

    messages: List[Any] = [HumanMessage(content=user_query)]
    tool_history: List[Dict[str, Any]] = []
    da_thu: List[str] = []
    trace_log: List[Dict[str, Any]] = []

    last_booking_code: Optional[str] = None
    stop_reason: str = "RUNNING"
    final_handoff: Optional[Dict[str, Any]] = None
    step_num = 0

    if verbose:
        print("\n" + "=" * 80)
        print(f"BẮT ĐẦU CHU TRÌNH REACT AGENT (Scenario {scenario})")
        print(f"Yêu cầu: {user_query}")
        print(f"Ràng buộc: {cons.origin} -> {cons.destination} ngày {cons.depart_date}, trần {cons.max_price:,}đ")
        print("=" * 80)

    # 3. VÒNG LẶP CHÍNH (THE AGENTIC LOOP)
    while True:
        step_num += 1

        # A. Kiểm tra ngân sách (BudgetManager)
        exceeded, budget_msg = budget.increment_step(tokens_used=600)
        if exceeded:
            stop_reason = "BUDGET_EXCEEDED"
            final_handoff = ban_giao(
                ly_do=budget_msg,
                da_thu=da_thu,
                trang_thai={"steps": step_num, "last_booking": last_booking_code},
                cau_hoi_cho_nguoi="Agent đã chạm trần số bước cho phép mà chưa xong. Bạn có muốn cấp thêm lượt?"
            )
            break

        # B. Model suy luận và đề xuất hành động tiếp theo
        ai_resp: AIMessage = model.invoke(messages)
        messages.append(ai_resp)

        tool_calls = getattr(ai_resp, "tool_calls", [])

        # C. Nếu Model không gọi tool nào nữa -> Model tự nhận hoàn tất hoặc dừng
        if not tool_calls:
            # LỚP 2: Kiểm chứng khách quan bằng code (Sensor Computational)
            completion_res = check_completion(last_booking_code, cons, tool_history)
            if completion_res["completed"]:
                stop_reason = "COMPLETED"
            else:
                stop_reason = "TERMINATED_WITHOUT_COMPLETION"
                final_handoff = ban_giao(
                    ly_do=f"Model dừng gọi tool nhưng Sensor kiểm tra không đạt: {completion_res['reason']}",
                    da_thu=da_thu,
                    trang_thai={"booking_code": last_booking_code, "checks": completion_res["checks"]},
                    cau_hoi_cho_nguoi="Model đã tuyên bố xong nhưng chưa đáp ứng đủ tiêu chí. Cần xử lý tiếp ra sao?"
                )

            trace_log.append({
                "step": step_num,
                "type": "thought_or_final",
                "content": ai_resp.content
            })
            if verbose:
                print(f"[Bước {step_num}] Model Kết luận: {ai_resp.content}")
            break

        # D. Xử lý từng tool_call do Model đề xuất
        action_stopped = False
        for call in tool_calls:
            tool_name = call["name"]
            tool_args = call["args"]
            call_id = call.get("id", f"call_{step_num}")

            call_signature = f"{tool_name}({tool_args})"
            da_thu.append(call_signature)

            if verbose:
                print(f"[Bước {step_num}] Model đề xuất Action: {call_signature}")

            # ------------------------------------------------------------------
            # LỚP 3: KIỂM QUYỀN TRƯỚC THỰC THI (PRE-EXECUTION AUTHORIZATION)
            # ------------------------------------------------------------------
            auth = auth_hook.evaluate(tool_name, tool_args)
            if not auth.allowed:
                stop_reason = "NEED_HUMAN_APPROVAL"
                cau_hoi = (
                    f"{auth.dang_o_dau} "
                    f"{auth.dinh_lam_gi} "
                    f"{auth.vi_sao_phai_hoi} "
                    f"Bạn có đồng ý phê duyệt tiếp tục không?"
                )
                final_handoff = ban_giao(
                    ly_do=auth.reason,
                    da_thu=da_thu,
                    trang_thai={"flight_no": tool_args.get("flight_no"), "action": tool_name},
                    cau_hoi_cho_nguoi=cau_hoi
                )
                if verbose:
                    print(f"\n[LỚP 3 KIỂM QUYỀN CHẶN ĐỨNG]")
                    print(f"  • Đang ở đâu: {auth.dang_o_dau}")
                    print(f"  • Định làm gì: {auth.dinh_lam_gi}")
                    print(f"  • Vì sao hỏi: {auth.vi_sao_phai_hoi}")
                action_stopped = True
                break

            # Tự động gán booking_code cho bước pay nếu có
            if tool_name == "pay" and last_booking_code and not tool_args.get("booking_code"):
                tool_args["booking_code"] = last_booking_code

            # ------------------------------------------------------------------
            # THỰC THI TOOL AN TOÀN
            # ------------------------------------------------------------------
            if tool_name not in TOOL_MAP:
                obs_data = {"status": "error", "error": f"Tool '{tool_name}' không tồn tại"}
            else:
                obs_data = TOOL_MAP[tool_name](**tool_args)

            # Lưu mã booking nếu có
            if isinstance(obs_data, dict):
                if "booking_code" in obs_data:
                    last_booking_code = obs_data["booking_code"]

            tool_msg_content = json.dumps(obs_data, ensure_ascii=False)
            messages.append(ToolMessage(content=tool_msg_content, tool_call_id=call_id))
            tool_history.append({"tool": tool_name, "args": tool_args, "observation": obs_data})

            if verbose:
                print(f"[Bước {step_num}] Observation: {tool_msg_content}")

            # ------------------------------------------------------------------
            # BỔ TRỢ: PHÁT HIỆN LẶP & BẾ TẮC (LOOP DETECTOR)
            # ------------------------------------------------------------------
            progress_metric = (1 if last_booking_code else 0) + (1 if isinstance(obs_data, dict) and obs_data.get("status") == "ok" else 0)
            loop_alert = loop_detector.check(tool_name, tool_args, observation=obs_data, progress=progress_metric)
            if loop_alert:
                stop_reason = "LOOP_DETECTED"
                final_handoff = ban_giao(
                    ly_do=loop_alert,
                    da_thu=da_thu,
                    trang_thai={"step_count": step_num, "observations_count": len(tool_history)},
                    cau_hoi_cho_nguoi="Phát hiện vòng lặp vô hạn hoặc bế tắc. Hãy chỉ định tuyến bay khác hoặc dừng agent."
                )
                if verbose:
                    print(f"\n[PHÁT HIỆN LẶP] {loop_alert}")
                action_stopped = True
                break

            trace_log.append({
                "step": step_num,
                "action": tool_name,
                "args": tool_args,
                "observation": obs_data
            })

        if action_stopped:
            break

        # E. LỚP 2: Kiểm tra hoàn thành sau mỗi vòng nếu đã có booking code
        if last_booking_code:
            completion_res = check_completion(last_booking_code, cons, tool_history)
            if completion_res["completed"]:
                stop_reason = "COMPLETED"
                if verbose:
                    print(f"\n[LỚP 2 SENSOR XÁC NHẬN HOÀN TẤT] {completion_res['reason']}")
                break

    # 4. TỔNG HỢP KẾT QUẢ VÀ CHỈ SỐ
    elapsed_ms = (time.time() - start_time) * 1000
    final_verification = check_completion(last_booking_code, cons, tool_history) if last_booking_code else {"completed": False}

    return {
        "agent": "ReAct",
        "scenario": scenario,
        "status": stop_reason,
        "is_success": (stop_reason == "COMPLETED") or (stop_reason == "NEED_HUMAN_APPROVAL" and scenario == 3) or (stop_reason == "LOOP_DETECTED" and scenario == 4),
        "steps": step_num,
        "stop_reason": stop_reason,
        "booking_code": last_booking_code,
        "verification": final_verification,
        "handoff": final_handoff,
        "da_thu": da_thu,
        "trace": trace_log,
        "metrics": {
            "latency_ms": round(elapsed_ms, 2),
            "estimated_tokens": budget.estimated_tokens,
            "tool_calls_count": len(da_thu),
        }
    }


if __name__ == "__main__":
    print("=== THỰC THI TEST NHANH REACT AGENT ===")
    reset_flight_database()
    res = run_react_agent("Tìm và đặt vé sáng từ SGN đi DAD ngày 2026-10-07", scenario=1, verbose=True)
    print("\nKết quả chạy:", res["status"], "| Số bước:", res["steps"])
