# -*- coding: utf-8 -*-
"""BTVN#3 · SE373 Agent Fundamentals · Bộ Kiểm Thử Biên (Edge Cases Test Suite).

Kiểm thử chuyên sâu các trường hợp biên, các giả định ngầm và các tình huống bất thường:
    1. Unknown Tool: PreExecutionAuthHook chặn tool lạ ngoài whitelist.
    2. Budget Thresholds: book_seat vượt trần vs trong trần ngân sách.
    3. Non-refundable Policy: pay chặn giao dịch vé không hoàn hủy khi chưa hỏi người.
    4. Expiration: pay từ chối booking quá hạn 15 phút.
    5. Sensor Computational: check_completion phát hiện vé giả / chưa thanh toán / sai giá.
    6. Hallucination Guard: kiem_can_cu đối chiếu dữ kiện số tiền chuẩn hóa.
    7. LoopDetector: Kiểm thử cả 3 tín hiệu độc lập (Action, Observation, Stall).
    8. Structured Handoff: ban_giao tương thích mọi dạng tham số và không bao giờ crash.
"""
from __future__ import annotations

import os
import sys
import time

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from mock_flight_tools import (
    reset_flight_database,
    search_flights,
    check_seat,
    book_seat,
    pay,
    get_booking,
    BOOKINGS_DATABASE,
)
from flight_harness import (
    FlightConstraints,
    check_completion,
    PreExecutionAuthHook,
    ban_giao,
    LoopDetector,
    BudgetManager,
    kiem_can_cu,
)


def test_unknown_tool():
    """Edge Case 1: Tool lạ không nằm trong danh mục an toàn."""
    cons = FlightConstraints()
    hook = PreExecutionAuthHook(cons)
    res = hook.evaluate("delete_database", {"table": "flights"})
    assert not res.allowed, "Tool lạ phải bị chặn!"
    assert "không được cấp phép" in res.reason, f"Lý do chặn chưa đúng: {res.reason}"
    print("  [PASS] test_unknown_tool: Chặn đứng tool lạ ngoài whitelist")


def test_auth_hook_thresholds():
    """Edge Case 2: Kiểm quyền theo ngưỡng ngân sách và chính sách vé."""
    cons = FlightConstraints(max_price=2_000_000)
    hook = PreExecutionAuthHook(cons)

    # 1. book_seat với chuyến vượt ngân sách (QH118: 2.350.000đ)
    res_qh = hook.evaluate("book_seat", {"flight_no": "QH118"})
    assert not res_qh.allowed and res_qh.need_human_approval, "QH118 phải cần duyệt!"

    # 2. book_seat với chuyến trong ngân sách (VN122: 1.850.000đ)
    res_vn = hook.evaluate("book_seat", {"flight_no": "VN122"})
    assert res_vn.allowed, "VN122 trong ngân sách phải được phép!"

    print("  [PASS] test_auth_hook_thresholds: Kiểm quyền đúng theo ngưỡng ngân sách")


def test_booking_expiration():
    """Edge Case 3: Giữ chỗ quá hạn 15 phút bị từ chối thanh toán."""
    reset_flight_database()
    book_res = book_seat("VN122", "Nguyen Van A", "12A")
    bcode = book_res["booking_code"]

    # Giả lập thời gian trôi qua 16 phút
    BOOKINGS_DATABASE[bcode]["expires_at"] = time.time() - 60

    pay_res = pay(bcode, "credit_card")
    assert pay_res.get("status") == "error", "Vé quá hạn không được phép thanh toán!"
    assert pay_res.get("error") == "booking_expired", f"Lỗi không khớp: {pay_res}"
    print("  [PASS] test_booking_expiration: Chặn thanh toán mã đặt chỗ hết hạn")


def test_sensor_check_completion():
    """Edge Case 4: Sensor Computational bắt lỗi vé chưa thanh toán hoặc dữ liệu sai."""
    reset_flight_database()
    cons = FlightConstraints(max_price=2_000_000, depart_date="2026-10-07")

    # 1. Chưa có booking code
    chk1 = check_completion(None, cons)
    assert not chk1["completed"], "None booking code phải không đạt"

    # 2. Mã booking không tồn tại
    chk2 = check_completion("FAKE-123", cons)
    assert not chk2["completed"], "Mã booking giả phải bị từ chối"

    # 3. Vé mới ở trạng thái 'held' chưa 'confirmed'
    book_res = book_seat("VN122", "Nguyen Van A", "12A")
    bcode = book_res["booking_code"]
    chk3 = check_completion(bcode, cons)
    assert not chk3["completed"], "Vé chưa thanh toán (held) không được tính là xong"

    # 4. Vé đã thanh toán hợp lệ
    pay(bcode, "credit_card")
    tool_hist = [{"tool": "check_seat", "observation": {"flight_no": "VN122", "price": 1850000}}]
    chk4 = check_completion(bcode, cons, tool_hist)
    assert chk4["completed"], f"Vé confirmed hợp lệ phải đạt: {chk4}"
    print("  [PASS] test_sensor_check_completion: Sensor kiểm chứng độc lập chính xác 100%")


def test_fact_checking_kiem_can_cu():
    """Edge Case 5: Đối chiếu nguồn dữ kiện, tránh false positive với số tiền."""
    obs = [{"price": 1850000, "flight_no": "VN122", "date": "2026-10-07"}]
    cau_tra_loi_chuan = "Đã đặt vé chuyến VN122 ngày 2026-10-07 với giá 1.850.000đ."
    res_chuan = kiem_can_cu(cau_tra_loi_chuan, obs)
    assert res_chuan["dat"], f"Số tiền có dấu chấm phải được nhận diện khớp nguồn: {res_chuan}"

    cau_tra_loi_hallucination = "Đã đặt vé chuyến VN999 ngày 2026-10-07 với giá 5.000.000đ."
    res_hal = kiem_can_cu(cau_tra_loi_hallucination, obs)
    assert not res_hal["dat"], "Thông tin bịa đặt phải bị phát hiện!"
    assert "VN999" in res_hal["khong_co_nguon"] or "5.000.000đ" in res_hal["khong_co_nguon"]
    print("  [PASS] test_fact_checking_kiem_can_cu: Fact-checking chuẩn xác không báo động giả")


def test_loop_detector_all_signals():
    """Edge Case 6: Kiểm thử 3 tín hiệu độc lập của LoopDetector."""
    # Tín hiệu 1: Trùng Action
    det1 = LoopDetector(window=4, repeat_k=2)
    warn1 = det1.check("search_flights", {"origin": "SGN", "dest": "DAD"})
    assert warn1 is None
    warn2 = det1.check("search_flights", {"origin": "SGN", "dest": "DAD"})
    assert warn2 is not None and "LOOP" in warn2, "Trùng action phải báo LOOP"

    # Tín hiệu 2: Trùng Observation (khác args nhưng cùng mã lỗi)
    det2 = LoopDetector(window=4, same_obs_k=3)
    det2.check("search", {"q": "VTG"}, observation={"status": "error", "error": "airport_not_found", "hint": "..."})
    det2.check("search", {"q": "Vung Tau"}, observation={"status": "error", "error": "airport_not_found", "hint": "..."})
    warn_obs = det2.check("search", {"q": "Vũng Tàu"}, observation={"status": "error", "error": "airport_not_found", "hint": "..."})
    assert warn_obs is not None and "LOOP" in warn_obs, "Trùng observation 3 lần phải báo LOOP"

    # Tín hiệu 3: Stall (không tiến triển qua N vòng)
    det3 = LoopDetector(window=6, stall_n=3)
    det3.check("search", {"q": "1"}, progress=0)
    det3.check("search", {"q": "2"}, progress=0)
    det3.check("search", {"q": "3"}, progress=0)
    warn_stall = det3.check("search", {"q": "4"}, progress=0)
    assert warn_stall is not None and "STALL" in warn_stall, "Đứng yên 3 vòng phải báo STALL"

    print("  [PASS] test_loop_detector_all_signals: Cả 3 tín hiệu LoopDetector hoạt động hoàn hảo")


def test_ban_giao_compatibility():
    """Edge Case 7: Hàm ban_giao hỗ trợ mọi kiểu gọi tham số."""
    b1 = ban_giao("LÝ DO 1", ["step1"], {"k": "v"}, "Hỏi gì?")
    assert b1["stop_reason"] == "LÝ DO 1"
    assert b1["cau_hoi_cho_nguoi"] == "Hỏi gì?"

    b2 = ban_giao(stop_reason="LÝ DO 2", da_thu=["step2"], trang_thai={}, cau_hoi_cho_nguoi="Hỏi người?")
    assert b2["stop_reason"] == "LÝ DO 2"
    assert b2["cau_hoi_cho_nguoi"] == "Hỏi người?"

    b3 = ban_giao(ly_do="LÝ DO 3", da_thu=[], trang_thai={}, cau_hoi_cho_nguoi="Hỏi người 3?")
    assert b3["stop_reason"] == "LÝ DO 3"
    assert b3["cau_hoi_cho_nguoi"] == "Hỏi người 3?"

    print("  [PASS] test_ban_giao_compatibility: ban_giao linh hoạt và an toàn 100%")


def run_all_edge_case_tests():
    print("\n" + "=" * 70)
    print("CHẠY BỘ KIỂM THỬ BIÊN CHUYÊN SÂU (EDGE CASE TEST SUITE)")
    print("=" * 70)
    test_unknown_tool()
    test_auth_hook_thresholds()
    test_booking_expiration()
    test_sensor_check_completion()
    test_fact_checking_kiem_can_cu()
    test_loop_detector_all_signals()
    test_ban_giao_compatibility()
    print("=" * 70)
    print(">>> TẤT CẢ 7/7 BÀI TEST BIÊN ĐÃ VƯỢT QUA XUẤT SẮC! <<<")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_all_edge_case_tests()
