# -*- coding: utf-8 -*-
"""BTVN#3 · SE373 Agent Fundamentals · Chương Trình Chính (CLI Runner).

Giao diện dòng lệnh tương tác và kiểm thử hệ thống Agent đặt vé máy bay:
    - Chạy đơn lẻ từng Agent (ReAct, Plan-then-Execute, Hybrid)
    - Thử nghiệm 4 kịch bản nghiệp vụ thực tế
    - Chạy toàn bộ Benchmark đánh giá so sánh hiệu năng
    - Tùy chọn sử dụng Model Giả Lập hoặc Model Thật (OpenAI/Gemini/Groq) qua .env

Cách sử dụng:
    # 1. Chạy đánh giá toàn diện Benchmark:
    python main.py --eval

    # 2. Chạy thử nghiệm mẫu ReAct ở Kịch bản 1 (Happy Path):
    python main.py --agent react --scenario 1 --verbose

    # 3. Chạy thử nghiệm mẫu Plan-then-Execute ở Kịch bản 2 (Biến động hết chỗ):
    python main.py --agent plan_execute --scenario 2 --verbose

    # 4. Chạy thử nghiệm mẫu Lai (Hybrid) ở Kịch bản 2 (Biến động & Replanning):
    python main.py --agent hybrid --scenario 2 --verbose

    # 5. Chạy thử nghiệm với câu hỏi tùy biến của người dùng:
    python main.py --agent react --query "Tìm vé từ SGN đi DAD ngày 2026-10-07" --verbose
"""
from __future__ import annotations

import argparse
import json
import os
import sys

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

from mock_flight_tools import reset_flight_database
from flight_harness import FlightConstraints, format_ban_giao
from model_provider import get_real_chat_model
from agent_react import run_react_agent
from agent_plan_execute import run_plan_execute_agent
from agent_hybrid import run_hybrid_agent
from evaluate_agents import run_benchmark, SCENARIOS


AGENT_MAP = {
    "react": run_react_agent,
    "plan_execute": run_plan_execute_agent,
    "hybrid": run_hybrid_agent
}


def print_banner() -> None:
    print("=" * 80)
    print("      HỆ THỐNG AI AGENT ĐẶT VÉ MÁY BAY · BTVN#3 · SE373 AGENT FUNDAMENTALS      ")
    print("       Đầy Đủ 4 Lớp Harness · So Sánh 3 Mẫu Thiết Kế: ReAct - Plan - Lai       ")
    print("=" * 80)


def execute_single_run(
    agent_name: str,
    scenario_id: int,
    custom_query: str = "",
    use_real_model: bool = False,
    verbose: bool = True
) -> None:
    """Thực thi một phiên chạy Agent cụ thể và in kết quả chi tiết."""
    runner = AGENT_MAP.get(agent_name.lower())
    if not runner:
        print(f"Lỗi: Không tìm thấy agent '{agent_name}'. Chọn: react | plan_execute | hybrid")
        return

    sc_data = SCENARIOS.get(scenario_id, SCENARIOS[1])
    query = custom_query.strip() or sc_data["query"]
    constraints = sc_data["constraints"]

    # Thiết lập model
    real_model = None
    if use_real_model:
        try:
            real_model = get_real_chat_model()
            print("[CẤU HÌNH] Sử dụng LLM Thật qua biến môi trường SE373_MODEL.")
        except Exception as e:
            print(f"[CẢNH BÁO] Không thể tải model thật: {e}")
            print("[CẤU HÌNH] Tự động chuyển về Model Giả Lập chuẩn hóa.")

    # Khôi phục trạng thái database
    reset_flight_database()

    print(f"\n[*] Đang khởi chạy Agent: {agent_name.upper()}")
    print(f"[*] Kịch bản {scenario_id}: {sc_data['title']}")
    print(f"[*] Câu hỏi: \"{query}\"")
    print(f"[*] Ràng buộc mục tiêu: {constraints.origin} -> {constraints.destination}, Ngày: {constraints.depart_date}, Trần: {constraints.max_price:,}đ")

    res = runner(
        user_query=query,
        constraints=constraints,
        scenario=scenario_id,
        custom_model=real_model,
        verbose=verbose
    )

    # In kết quả tổng hợp
    print("\n" + "-" * 80)
    print("KẾT QUẢ PHIÊN CHẠY:")
    print(f"  • Mẫu thiết kế : {res['agent']}")
    print(f"  • Trạng thái   : {res['status']}")
    print(f"  • Đạt chuẩn    : {'✓ ĐẠT MỤC TIÊU / AN TOÀN' if res['is_success'] else '✗ THẤT BẠI'}")
    print(f"  • Số bước chạy : {res['steps']}")
    print(f"  • Độ trễ xử lý : {res['metrics']['latency_ms']} ms")
    print(f"  • Tool đã gọi  : {' → '.join(res['da_thu']) or 'Không'}")

    if res.get("booking_code"):
        print(f"  • Mã đặt chỗ   : {res['booking_code']}")

    if res.get("verification", {}).get("completed"):
        print(f"  • Sensor Lớp 2 : XÁC MINH HỢP LỆ BẰNG CODE (Confirmed, Paid, Within Budget)")
    elif res.get("verification", {}).get("reason"):
        print(f"  • Sensor Lớp 2 : {res['verification']['reason']}")

    # In khối bàn giao nếu có
    if res.get("handoff"):
        print("\n" + format_ban_giao(res["handoff"]))

    print("-" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="BTVN#3 · Dựng Agent Đặt Vé Máy Bay bằng LangChain & LangGraph (SE373)",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--agent",
        type=str,
        default="all",
        choices=["react", "plan_execute", "hybrid", "all"],
        help="Chọn mẫu thiết kế agent cần chạy (react, plan_execute, hybrid, all)"
    )
    parser.add_argument(
        "--scenario",
        type=int,
        default=1,
        choices=[1, 2, 3, 4],
        help="Chọn kịch bản kiểm thử (1: Happy Path, 2: Volatility, 3: Auth, 4: Loop)"
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Chạy toàn bộ benchmark 4 kịch bản cho cả 3 agent và in bảng so sánh"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="",
        help="Câu hỏi tuỳ biến từ người dùng (ghi đè kịch bản mặc định)"
    )
    parser.add_argument(
        "--model-that",
        action="store_true",
        help="Sử dụng LLM thật qua cấu hình trong .env thay vì model giả lập"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="In chi tiết trace log từng bước suy luận và hành động"
    )

    args = parser.parse_args()
    print_banner()

    if args.eval:
        run_benchmark(verbose_level=2 if args.verbose else 1)
        return

    if args.agent == "all":
        for a_name in ["react", "plan_execute", "hybrid"]:
            execute_single_run(
                agent_name=a_name,
                scenario_id=args.scenario,
                custom_query=args.query,
                use_real_model=args.model_that,
                verbose=args.verbose
            )
    else:
        execute_single_run(
            agent_name=args.agent,
            scenario_id=args.scenario,
            custom_query=args.query,
            use_real_model=args.model_that,
            verbose=args.verbose
        )


if __name__ == "__main__":
    main()
