# -*- coding: utf-8 -*-
"""BTVN#3 · SE373 Agent Fundamentals · Bộ 4 Lớp Harness Toàn Diện.

Đây là phần framework KHÔNG làm hộ. Cả 4 lớp đều là logic Python xác định,
chạy trong vài mili-giây, không tốn token LLM, đảm bảo an toàn tuyệt đối:
    1. Ràng buộc là dữ liệu (FlightConstraints dataclass & validator)
    2. Tiêu chí hoàn thành kiểm bằng code (Sensor Computational - check_completion)
    3. Kiểm quyền trước thực thi (PreExecutionAuthHook - Human Approval)
    4. Bàn giao có cấu trúc (ban_giao - Stop reason & 30s handoff)

Kèm theo các cơ chế bổ trợ chuẩn Slide 41-49:
    - LoopDetector: Phát hiện lặp action, lặp observation, và bế tắc (stall).
    - BudgetManager: Quản lý trần số bước và ước tính token.
    - kiem_can_cu: Đối chiếu dữ kiện số liệu để triệt tiêu Hallucination.
"""
from __future__ import annotations

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

from collections import deque
from dataclasses import dataclass, field
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from mock_flight_tools import get_booking, FLIGHT_DATABASE


# ==============================================================================
# LỚP 1: RÀNG BUỘC LÀ DỮ LIỆU (CONSTRAINTS AS DATA) - SLIDE 60-62
# ==============================================================================

@dataclass(frozen=True)
class FlightConstraints:
    """Cấu trúc dữ liệu bất biến lưu trữ ràng buộc mục tiêu của người dùng.

    Không để ràng buộc trôi dạt trong chat history dạng câu văn tự do.
    Harness lưu cấu trúc này tại vị trí cố định để kiểm tra đối chiếu.
    """
    origin: str = "SGN"                    # Sân bay đi (VD: SGN - Tân Sơn Nhất)
    destination: str = "DAD"               # Sân bay đến (VD: DAD - Đà Nẵng)
    depart_date: str = "2026-10-07"        # Ngày khởi hành (YYYY-MM-DD)
    max_price: int = 2_000_000             # Trần ngân sách tối đa (VNĐ)
    time_preference: str = "sang"          # Khung giờ ưu tiên ("sang": trước 12:00)
    require_refundable: bool = True        # Bắt buộc phải là loại vé được hoàn/hủy
    passenger_name: str = "Nguyen Van A"   # Tên hành khách đặt vé
    seat_preference: str = "12A"           # Chỗ ngồi mong muốn

    def to_dict(self) -> Dict[str, Any]:
        return {
            "origin": self.origin,
            "destination": self.destination,
            "depart_date": self.depart_date,
            "max_price": self.max_price,
            "time_preference": self.time_preference,
            "require_refundable": self.require_refundable,
            "passenger_name": self.passenger_name,
            "seat_preference": self.seat_preference,
        }


def validate_constraints(booking: Dict[str, Any], constraints: FlightConstraints) -> Dict[str, Any]:
    """Đối chiếu thông tin booking với các ràng buộc dữ liệu ban đầu."""
    violations: List[str] = []

    # 1. Kiểm tra ngày bay
    if booking.get("depart_date") != constraints.depart_date:
        violations.append(
            f"Ngày bay {booking.get('depart_date')} không khớp yêu cầu {constraints.depart_date}"
        )

    # 2. Kiểm tra giá vé
    price = booking.get("price", float("inf"))
    if price > constraints.max_price:
        violations.append(
            f"Giá vé {price:,}đ vượt ngân sách tối đa {constraints.max_price:,}đ"
        )

    # 3. Kiểm tra giờ bay (nếu ưu tiên chuyến sáng < 12:00)
    depart_time = booking.get("depart_time", "")
    if constraints.time_preference == "sang" and depart_time:
        hour = int(depart_time.split(":")[0])
        if hour >= 12:
            violations.append(f"Giờ khởi hành {depart_time} không thuộc buổi sáng (< 12:00)")

    # 4. Kiểm tra chính sách hoàn hủy
    if constraints.require_refundable and not booking.get("refundable", False):
        violations.append("Vé không hỗ trợ hoàn hủy theo yêu cầu ban đầu")

    return {
        "valid": len(violations) == 0,
        "violations": violations
    }


# ==============================================================================
# LỚP 2: TIÊU CHÍ HOÀN THÀNH KIỂM BẰNG CODE (SENSOR COMPUTATIONAL) - SLIDE 43-44
# ==============================================================================

def check_completion(
    booking_code: Optional[str],
    constraints: FlightConstraints,
    tool_history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Sensor Computational: Kiểm chứng logic khách quan, không tin lời model.

    Hàm này gọi trực tiếp API database nội bộ get_booking để kiểm tra trạng thái
    thực tế của vé, đồng thời đối chiếu chéo (cross-verification) với lịch sử
    các quan sát (observations) đã nhận.
    """
    if not booking_code:
        return {
            "completed": False,
            "reason": "Chưa có mã đặt chỗ (booking_code)",
            "checks": {}
        }

    # 1. Gọi trực tiếp API get_booking để tra cứu trạng thái bản ghi
    res = get_booking(booking_code)
    if res.get("status") != "ok" or not res.get("booking"):
        return {
            "completed": False,
            "reason": f"Mã đặt chỗ {booking_code} không tồn tại trong hệ thống",
            "checks": {"booking_exists": False}
        }

    booking = res["booking"]

    # 2. Kiểm tra các vị từ logic cốt lõi
    is_confirmed = (booking.get("state") == "confirmed")
    is_paid = (booking.get("paid") is True)
    is_within_budget = (booking.get("price", float("inf")) <= constraints.max_price)
    date_matched = (booking.get("depart_date") == constraints.depart_date)
    passenger_matched = (booking.get("passenger_name") == constraints.passenger_name)
    refundable_matched = (
        not constraints.require_refundable or booking.get("refundable") is True
    )

    # 3. Kiểm chứng chéo (Cross-verification):
    # Giá vé và chuyến bay trong booking phải khớp với kết quả từng thấy trong quan sát trước đó
    cross_verified_price = False
    cross_verified_flight = False

    history = tool_history or []
    for item in history:
        obs = item.get("observation", {})
        if isinstance(obs, str):
            try:
                obs = json.loads(obs)
            except Exception:
                continue

        # Kiểm tra qua check_seat
        if obs.get("flight_no") == booking.get("flight_no"):
            cross_verified_flight = True
            if obs.get("price") == booking.get("price"):
                cross_verified_price = True
                break

        # Hoặc kiểm tra qua search_flights
        if "flights" in obs:
            for f in obs["flights"]:
                if f.get("flight_no") == booking.get("flight_no"):
                    cross_verified_flight = True
                    if f.get("base_price") == booking.get("price"):
                        cross_verified_price = True
                        break

    # Nếu history rỗng thì chấp nhận nếu booking tồn tại hợp lệ
    if not history:
        cross_verified_price = True
        cross_verified_flight = True

    checks = {
        "booking_exists": True,
        "status_confirmed": is_confirmed,
        "paid": is_paid,
        "within_budget": is_within_budget,
        "date_matched": date_matched,
        "passenger_matched": passenger_matched,
        "refundable_matched": refundable_matched,
        "cross_verified_flight": cross_verified_flight,
        "cross_verified_price": cross_verified_price,
    }

    all_passed = all(checks.values())

    reason = "Mục tiêu hoàn thành mỹ mãn: Vé confirmed, đã thanh toán, chuẩn dữ liệu và trong ngân sách"
    if not all_passed:
        failed_items = [k for k, v in checks.items() if not v]
        reason = f"Chưa đạt tiêu chí hoàn thành: Các mục chưa thỏa mãn [{', '.join(failed_items)}]"

    return {
        "completed": all_passed,
        "reason": reason,
        "booking_code": booking_code,
        "booking_details": booking,
        "checks": checks
    }


# ==============================================================================
# LỚP 3: KIỂM QUYỀN TRƯỚC THỰC THI (PRE-EXECUTION AUTHORIZATION) - SLIDE 35, 41
# ==============================================================================

@dataclass
class AuthCheckResult:
    """Kết quả kiểm quyền trước khi thực thi tool."""
    allowed: bool
    need_human_approval: bool = False
    reason: str = "Thao tác hợp lệ trong thẩm quyền"
    dang_o_dau: str = ""
    dinh_lam_gi: str = ""
    vi_sao_phai_hoi: str = ""


class PreExecutionAuthHook:
    """Lớp kiểm quyền độc lập chạy trước khi thực thi bất kỳ tool nào.

    Ngăn chặn Điều kiện dừng số 5: Chạm tới hành động nhạy cảm vượt thẩm quyền
    hoặc tác dụng phụ tài chính không thể đảo ngược.
    """

    def __init__(self, constraints: FlightConstraints, auto_approve_safe_actions: bool = True):
        self.constraints = constraints
        self.auto_approve_safe_actions = auto_approve_safe_actions

    def evaluate(self, tool_name: str, tool_args: Dict[str, Any], context_state: Optional[Dict[str, Any]] = None) -> AuthCheckResult:
        """Đánh giá thẩm quyền của hành động trước khi gọi tool."""
        state = context_state or {}

        # 0. Chặn công cụ lạ không nằm trong danh mục (Whitelist an toàn)
        KNOWN_TOOLS = {"search_flights", "check_seat", "book_seat", "pay", "get_booking"}
        if tool_name not in KNOWN_TOOLS:
            return AuthCheckResult(
                allowed=False,
                need_human_approval=False,
                reason=f"Công cụ '{tool_name}' không được cấp phép trong hệ thống",
                dang_o_dau="Hệ thống chuẩn bị gọi công cụ ngoại lai.",
                dinh_lam_gi=f"Định thực thi '{tool_name}'.",
                vi_sao_phai_hoi="Công cụ không nằm trong danh mục an toàn được phê duyệt."
            )

        # 1. Các tool chỉ đọc (read-only): Luôn an toàn
        if tool_name in ["search_flights", "check_seat", "get_booking"]:
            return AuthCheckResult(allowed=True)

        # 2. Kiểm tra thao tác book_seat (Giữ chỗ)
        if tool_name == "book_seat":
            flight_no = tool_args.get("flight_no", "")
            # Tra cứu thông tin chuyến bay định đặt
            flight = next((f for f in FLIGHT_DATABASE if f["flight_no"] == flight_no), None)
            if flight:
                price = flight["base_price"]
                # Nếu giá vé vượt trần ngân sách ràng buộc -> Phải hỏi người dùng
                if price > self.constraints.max_price:
                    return AuthCheckResult(
                        allowed=False,
                        need_human_approval=True,
                        reason="Giá vé vượt trần ngân sách cho phép",
                        dang_o_dau=f"Đã kiểm tra chuyến bay {flight_no} từ {flight['origin']} đi {flight['destination']} lúc {flight['depart_time']}.",
                        dinh_lam_gi=f"Định giữ chỗ chuyến bay {flight_no} với giá {price:,}đ.",
                        vi_sao_phai_hoi=f"Giá vé {price:,}đ vượt ngân sách tối đa ({self.constraints.max_price:,}đ)."
                    )

        # 3. Kiểm tra thao tác pay (thanh toán tiền thật - hành động nhạy cảm cao)
        if tool_name == "pay":
            booking_code = tool_args.get("booking_code", "")
            res = get_booking(booking_code)
            if res.get("status") == "ok":
                b = res["booking"]
                # Nếu giá vé vượt ngân sách hoặc là vé không hoàn hủy -> Cần con người phê duyệt
                if b["price"] > self.constraints.max_price or not b.get("refundable", True):
                    ly_do_list = []
                    if b["price"] > self.constraints.max_price:
                        ly_do_list.append(f"Giá vé {b['price']:,}đ vượt ngân sách tối đa ({self.constraints.max_price:,}đ)")
                    if not b.get("refundable", True):
                        ly_do_list.append("Vé thuộc loại KHÔNG HOÀN HỦY (Non-refundable)")
                    return AuthCheckResult(
                        allowed=False,
                        need_human_approval=True,
                        reason="Hành động trừ tiền thật vượt thẩm quyền tự chủ",
                        dang_o_dau=f"Đang nắm giữ mã đặt chỗ {booking_code} cho chuyến {b['flight_no']} ({b['depart_date']} {b['depart_time']}).",
                        dinh_lam_gi=f"Định thanh toán thực tế số tiền {b['price']:,}đ qua {tool_args.get('payment_method', 'thẻ')}.",
                        vi_sao_phai_hoi="; ".join(ly_do_list) + "."
                    )

        return AuthCheckResult(allowed=True)


# ==============================================================================
# LỚP 4: BÀN GIAO CÓ CẤU TRÚC (STRUCTURED HANDOFF) - SLIDE 48, 50
# ==============================================================================

def ban_giao(
    ly_do: str = "",
    da_thu: Optional[List[str]] = None,
    trang_thai: Optional[Dict[str, Any]] = None,
    cau_hoi: str = "",
    *,
    stop_reason: Optional[str] = None,
    cau_hoi_cho_nguoi: Optional[str] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    """Bàn giao có cấu trúc khi agent dừng bất thường, tuyệt đối không im lặng (Slide 50).

    Đảm bảo 4 trường thông tin giúp người nhận hiểu và quyết định trong < 30 giây.
    Hỗ trợ linh hoạt cả positional và keyword arguments.
    """
    actual_reason = stop_reason or ly_do or kwargs.get("reason", "DỪNG BẤT THƯỜNG")
    actual_cau_hoi = cau_hoi_cho_nguoi or cau_hoi or kwargs.get("cau_hoi", "") or ""
    return {
        "stop_reason": actual_reason,
        "da_thu": da_thu if da_thu is not None else [],
        "trang_thai": trang_thai if trang_thai is not None else {},
        "cau_hoi_cho_nguoi": actual_cau_hoi
    }


def format_ban_giao(b: Dict[str, Any]) -> str:
    """Format báo cáo bàn giao hiển thị trực quan cho người dùng."""
    da_thu_str = " → ".join(b.get("da_thu", [])) or "Chưa thực hiện thao tác nào"
    return (
        "╔════════════════════════════════════════════════════════════════════════════════╗\n"
        f"║ BÀN GIAO CHO CON NGƯỜI (HUMAN HANDOFF) · LÝ DO: {b.get('stop_reason')} \n"
        "╠════════════════════════════════════════════════════════════════════════════════╣\n"
        f"  • Đã thử          : {da_thu_str}\n"
        f"  • Trạng thái      : {json.dumps(b.get('trang_thai', {}), ensure_ascii=False)}\n"
        f"  • Hỏi người dùng  : {b.get('cau_hoi_cho_nguoi', '')}\n"
        "╚════════════════════════════════════════════════════════════════════════════════╝"
    )


# ==============================================================================
# CƠ CHẾ BỔ TRỢ: BỘ PHÁT HIỆN LẶP (LOOP DETECTOR) - SLIDE 45-48
# ==============================================================================

class LoopDetector:
    """Bộ phát hiện lặp và bế tắc theo đúng chuẩn Slide 48 (Buổi 03).

    Ba tín hiệu phát hiện:
    1. Trùng action: Cùng (tool, args) lặp lại trong cửa sổ vài vòng.
    2. Trùng observation: Tham số khác nhau nhưng kết quả trả về giống hệt.
    3. Không tiến triển (Stall): Đại lượng tiến triển đứng yên qua N vòng liên tiếp.
    """

    def __init__(self, window: int = 6, repeat_k: int = 2, same_obs_k: int = 3, stall_n: int = 3):
        self.recent = deque(maxlen=window)   # Lưu vân tay (tool, args)
        self.obs = deque(maxlen=window)      # Lưu vân tay observation
        self.k = repeat_k
        self.k_obs = same_obs_k
        self.n = stall_n
        self.last_progress = None
        self.stall_count = 0

    def check(
        self,
        tool: str,
        args: Dict[str, Any],
        observation: Optional[Any] = None,
        progress: Optional[Any] = None
    ) -> Optional[str]:
        """Kiểm tra dấu hiệu lặp hoặc bế tắc. Trả về thông báo cảnh báo nếu có lỗi."""
        # Tín hiệu 1: Trùng Action
        sorted_args = repr(sorted(args.items())) if isinstance(args, dict) else repr(args)
        fp = (tool, sorted_args)
        current_count = self.recent.count(fp) + 1
        if current_count >= self.k:
            return f"LOOP · '{tool}' gọi {current_count} lần với cùng tham số trong {self.recent.maxlen} vòng gần nhất"
        self.recent.append(fp)

        # Tín hiệu 2: Trùng Observation
        if observation is not None:
            # Chuẩn hóa để nhận diện lỗi lặp ngay cả khi query parameters đổi
            if isinstance(observation, dict):
                if observation.get("status") == "error":
                    ofp = f"error:{observation.get('error')}:{observation.get('hint', '')}"
                else:
                    obs_clean = {k: v for k, v in observation.items() if not k.startswith("queried_")}
                    ofp = repr(sorted(obs_clean.items()))
            else:
                ofp = repr(observation)

            obs_count = self.obs.count(ofp) + 1
            if obs_count >= self.k_obs:
                return f"LOOP · {obs_count} lời gọi khác tham số nhưng trả về cùng một kết quả giống hệt"
            self.obs.append(ofp)

        # Tín hiệu 3: Không tiến triển (Stall)
        if progress is not None:
            if progress == self.last_progress:
                self.stall_count += 1
            else:
                self.stall_count = 0
            self.last_progress = progress

            if self.stall_count >= self.n:
                return f"STALL · tiến triển đứng yên ở mức {progress!r} qua {self.stall_count} vòng"

        return None


# ==============================================================================
# CƠ CHẾ BỔ TRỢ: QUẢN LÝ NGÂN SÁCH (BUDGET MANAGER) - SLIDE 15, 38
# ==============================================================================

class BudgetManager:
    """Quản lý trần số bước lặp và ước lượng token tiêu thụ."""

    def __init__(self, max_steps: int = 10, max_tokens: int = 15_000):
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.current_step = 0
        self.estimated_tokens = 0

    def increment_step(self, tokens_used: int = 500) -> Tuple[bool, Optional[str]]:
        """Tăng số bước và kiểm tra xem có vượt trần không."""
        self.current_step += 1
        self.estimated_tokens += tokens_used

        if self.current_step > self.max_steps:
            return True, f"BUDGET_EXCEEDED · Vượt trần số bước cho phép ({self.current_step}/{self.max_steps})"

        if self.estimated_tokens > self.max_tokens:
            return True, f"TOKEN_EXCEEDED · Vượt trần token ước tính ({self.estimated_tokens}/{self.max_tokens})"

        return False, None


# ==============================================================================
# CƠ CHẾ BỔ TRỢ: KIỂM TRA CĂN CỨ DỮ KIỆN (FACT-CHECKING) - SLIDE 61-62
# ==============================================================================

MAU_DU_KIEN = [
    r"\d{1,3}(?:\.\d{3})+(?:đ|\s?VNĐ|\s?đồng)?",   # 1.850.000đ
    r"\d{1,2}:\d{2}",                              # 08:30
    r"\d{4}-\d{2}-\d{2}",                          # 2026-10-07
    r"\b[A-Z]{2}\d{3,4}\b",                        # VN122, VJ602
    r"[A-Z]{2}-BK\d+",                             # VN-BK101
    r"\b(?:SGN|DAD|HAN|CXR|PQC)\b",                # Mã sân bay
]


def trich_du_kien(text: str) -> List[str]:
    """Trích xuất tất cả các thực thể số tiền, ngày giờ, mã hiệu trong văn bản."""
    ra = []
    for mau in MAU_DU_KIEN:
        ra += re.findall(mau, text)
    return list(dict.fromkeys(ra))


def kiem_can_cu(cau_tra_loi: str, tool_observations: List[Any]) -> Dict[str, Any]:
    """Đối chiếu câu trả lời với các quan sát thực tế để ngăn chặn Hallucination."""
    nguon = " ".join(str(x) for x in tool_observations)
    nguon_normalized = re.sub(r"[\.,\sđVNĐđồng]", "", nguon)
    chi_tiet = []
    thieu = []
    for d in trich_du_kien(cau_tra_loi):
        d_clean = re.sub(r"[\.,\sđVNĐđồng]", "", d)
        co_nguon = (d in nguon) or (len(d_clean) > 0 and d_clean in nguon_normalized)
        chi_tiet.append({"du_kien": d, "co_nguon": co_nguon})
        if not co_nguon:
            thieu.append(d)
    return {
        "dat": len(thieu) == 0,
        "chi_tiet": chi_tiet,
        "khong_co_nguon": thieu
    }


if __name__ == "__main__":
    print("=== KIỂM THỬ FLIGHT_HARNESS ĐỘC LẬP ===")
    constraints = FlightConstraints()
    print("1. Ràng buộc mục tiêu:", constraints)

    # Thử nghiệm LoopDetector
    det = LoopDetector(window=4, repeat_k=2)
    print("2. LoopDetector thử nghiệm trùng action:")
    for v, dest in enumerate(["VTG", "VTG"], 1):
        warn = det.check("search_flights", {"origin": "SGN", "destination": dest})
        print(f"   Vòng {v}: {warn or 'bình thường'}")

    # Thử nghiệm PreExecutionAuthHook
    hook = PreExecutionAuthHook(constraints)
    auth_res = hook.evaluate("book_seat", {"flight_no": "QH118"})
    print("3. PreExecutionAuthHook với QH118 (vượt ngân sách):")
    print(f"   Allowed: {auth_res.allowed}, Need Approval: {auth_res.need_human_approval}")
    print(f"   Vì sao phải hỏi: {auth_res.vi_sao_phai_hoi}")
    print("=== HOÀN TẤT KIỂM THỬ HARNESS ===")
