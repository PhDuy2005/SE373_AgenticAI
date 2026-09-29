# -*- coding: utf-8 -*-
"""BTVN#3 · SE373 Agent Fundamentals · Bộ Mockup Tools Nghiệp Vụ Hàng Không.

Bộ công cụ giả lập nghiệp vụ tìm kiếm, kiểm tra ghế, giữ chỗ và thanh toán vé máy bay.
Tuân thủ nguyên tắc ở Slide 13 & 65 (Buổi 03):
- Dữ liệu tĩnh, có thể tái lặp (reproducible), không gọi API mạng tốn kém.
- Observation là giao diện điều khiển của Agent: Luôn trả kết quả có cấu trúc JSON,
  kèm mã lỗi và hướng dẫn khắc phục (hint) rõ ràng khi thất bại.
- Biến môi trường SE373_LOI_TE=1 kích hoạt chế độ "observation tệ" (trả lỗi cộc lốc),
  dùng để thử nghiệm các failure modes (lặp vô hạn) như trong Demo 2.
"""
from __future__ import annotations

import copy
import json
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional

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

# ==============================================================================
# 1. CƠ SỞ DỮ LIỆU CHUYẾN BAY MẪU (STATIC AIRLINE DATABASE)
# ==============================================================================

ORIGINAL_FLIGHT_DATABASE: List[Dict[str, Any]] = [
    {
        "flight_no": "VN122",
        "airline": "Vietnam Airlines",
        "origin": "SGN",
        "destination": "DAD",
        "depart_date": "2026-10-07",
        "depart_time": "08:30",
        "arrive_time": "10:00",
        "base_price": 1_850_000,
        "available_seats": 5,
        "seat_class": "Economy",
        "refundable": True,
        "note": "Chuyến sáng đúng yêu cầu, giá trong ngân sách (1.850.000đ), được hoàn hủy."
    },
    {
        "flight_no": "VJ602",
        "airline": "Vietjet Air",
        "origin": "SGN",
        "destination": "DAD",
        "depart_date": "2026-10-07",
        "depart_time": "06:15",
        "arrive_time": "07:35",
        "base_price": 1_350_000,
        "available_seats": 0,  # HẾT CHỖ - Dùng để thử nghiệm biến động môi trường / Replanning
        "seat_class": "Eco",
        "refundable": False,
        "note": "Giá rẻ nhất (1.350.000đ) nhưng hết chỗ (0 ghế). Agent cần biết đổi chuyến."
    },
    {
        "flight_no": "QH118",
        "airline": "Bamboo Airways",
        "origin": "SGN",
        "destination": "DAD",
        "depart_date": "2026-10-07",
        "depart_time": "11:00",
        "arrive_time": "12:20",
        "base_price": 2_350_000,
        "available_seats": 3,
        "seat_class": "Economy Flex",
        "refundable": False,  # VƯỢT HẠN MỨC & KHÔNG HOÀN HỦY - Dùng để test Kiểm quyền (Lớp 3)
        "note": "Giá 2.350.000đ vượt ngân sách 2.000.000đ và không hoàn tiền. Cần phê duyệt."
    },
    {
        "flight_no": "VN124",
        "airline": "Vietnam Airlines",
        "origin": "SGN",
        "destination": "DAD",
        "depart_date": "2026-10-07",
        "depart_time": "09:45",
        "arrive_time": "11:15",
        "base_price": 1_920_000,
        "available_seats": 2,
        "seat_class": "Economy Classic",
        "refundable": True,
        "note": "Chuyến bay thay thế hợp lệ (trong ngân sách, được hoàn hủy) khi VJ602 hết chỗ."
    }
]

# Bộ nhớ trạng thái thời gian chạy (runtime storage)
FLIGHT_DATABASE: List[Dict[str, Any]] = copy.deepcopy(ORIGINAL_FLIGHT_DATABASE)
BOOKINGS_DATABASE: Dict[str, Dict[str, Any]] = {}
BOOKING_COUNTER: int = 100


def reset_flight_database() -> None:
    """Khôi phục lại dữ liệu chuyến bay và danh sách booking về trạng thái ban đầu."""
    global BOOKING_COUNTER
    FLIGHT_DATABASE.clear()
    FLIGHT_DATABASE.extend(copy.deepcopy(ORIGINAL_FLIGHT_DATABASE))
    BOOKINGS_DATABASE.clear()
    BOOKING_COUNTER = 100


def _loi_te() -> bool:
    """Kiểm tra biến môi trường SE373_LOI_TE (Observation cộc lốc/thiếu thông tin)."""
    return os.environ.get("SE373_LOI_TE") == "1"


def _chuan_hoa(text: str) -> str:
    """Chuẩn hóa chuỗi văn bản (chữ thường, xóa khoảng trắng thừa)."""
    return " ".join(str(text).strip().upper().split())


# ==============================================================================
# 2. ĐỊNH NGHĨA 5 CÔNG CỤ MOCKUP NGHIỆP VỤ HÀNG KHÔNG
# ==============================================================================

def search_flights(origin: str, destination: str, date: str) -> Dict[str, Any]:
    """Tìm kiếm các chuyến bay theo sân bay đi, sân bay đến và ngày khởi hành.

    Tham số:
        origin: Mã sân bay đi (VD: 'SGN', 'HAN')
        destination: Mã sân bay đến (VD: 'DAD', 'HAN')
        date: Ngày khởi hành định dạng 'YYYY-MM-DD' (VD: '2026-10-07')

    Trả về:
        Dictionary chứa danh sách các chuyến bay phù hợp và số lượng kết quả.
    """
    orig_clean = _chuan_hoa(origin)
    dest_clean = _chuan_hoa(destination)
    date_clean = str(date).strip()

    # Kiểm tra tính hợp lệ của sân bay
    valid_airports = {"SGN", "DAD", "HAN", "CXR", "PQC"}
    if orig_clean not in valid_airports or dest_clean not in valid_airports:
        if _loi_te():
            return {"error": "not found"}
        return {
            "status": "error",
            "error": "airport_not_found",
            "queried_origin": origin,
            "queried_destination": destination,
            "hint": "Sân bay không hỗ trợ hoặc không có chuyến bay thương mại. Hãy dùng mã sân bay hợp lệ như SGN, DAD, HAN.",
            "supported_airports": sorted(list(valid_airports))
        }

    matched = [
        f for f in FLIGHT_DATABASE
        if _chuan_hoa(f["origin"]) == orig_clean
        and _chuan_hoa(f["destination"]) == dest_clean
        and f["depart_date"] == date_clean
    ]

    if not matched:
        if _loi_te():
            return {"error": "not found"}
        return {
            "status": "error",
            "error": "flights_not_found",
            "queried": {"origin": origin, "destination": destination, "date": date},
            "hint": "Không tìm thấy chuyến bay thẳng vào ngày này. Hãy thử kiểm tra ngày 2026-10-07 hoặc chặng SGN-DAD.",
            "supported_routes": ["SGN-DAD"]
        }

    # Trả về danh sách chuyến bay định dạng chuẩn
    sanitized_results = [
        {
            "flight_no": f["flight_no"],
            "airline": f["airline"],
            "origin": f["origin"],
            "destination": f["destination"],
            "depart_time": f["depart_time"],
            "arrive_time": f["arrive_time"],
            "base_price": f["base_price"],
            "available_seats": f["available_seats"],
            "seat_class": f["seat_class"],
            "refundable": f["refundable"],
            "note": f["note"]
        }
        for f in matched
    ]

    return {
        "status": "ok",
        "matched": len(matched),
        "depart_date": date_clean,
        "flights": sanitized_results
    }


def check_seat(flight_no: str) -> Dict[str, Any]:
    """Kiểm tra số ghế trống thực tế, giá vé và điều kiện hoàn hủy của chuyến bay.

    Tham số:
        flight_no: Mã hiệu chuyến bay (VD: 'VN122', 'VJ602', 'QH118')

    Trả về:
        Chi tiết số ghế trống và chính sách giá của chuyến bay.
    """
    f_code = _chuan_hoa(flight_no)
    flight = next((f for f in FLIGHT_DATABASE if _chuan_hoa(f["flight_no"]) == f_code), None)

    if not flight:
        if _loi_te():
            return {"error": "flight not found"}
        all_codes = [f["flight_no"] for f in FLIGHT_DATABASE]
        return {
            "status": "error",
            "error": "flight_not_found",
            "queried_flight": flight_no,
            "hint": "Mã chuyến bay không tồn tại trong hệ thống. Hãy gọi search_flights để lấy danh sách mã hợp lệ.",
            "valid_flights": all_codes
        }

    return {
        "status": "ok",
        "flight_no": flight["flight_no"],
        "airline": flight["airline"],
        "depart_date": flight["depart_date"],
        "depart_time": flight["depart_time"],
        "arrive_time": flight["arrive_time"],
        "available_seats": flight["available_seats"],
        "price": flight["base_price"],
        "seat_class": flight["seat_class"],
        "refundable": flight["refundable"],
        "note": flight["note"]
    }


def book_seat(flight_no: str, passenger_name: str, seat_code: str = "12A") -> Dict[str, Any]:
    """Tạo giữ chỗ tạm thời (Hold Seat) cho một hành khách trên chuyến bay cụ thể.

    Tham số:
        flight_no: Mã chuyến bay (VD: 'VN122')
        passenger_name: Họ tên đầy đủ của hành khách
        seat_code: Vị trí ghế mong muốn (mặc định: '12A')

    Trả về:
        Mã đặt chỗ tạm thời (booking_code) và trạng thái 'held' (chưa thanh toán).
    """
    global BOOKING_COUNTER
    f_code = _chuan_hoa(flight_no)
    flight = next((f for f in FLIGHT_DATABASE if _chuan_hoa(f["flight_no"]) == f_code), None)

    if not flight:
        if _loi_te():
            return {"error": "flight not found"}
        return {
            "status": "error",
            "error": "flight_not_found",
            "queried_flight": flight_no,
            "hint": "Không tìm thấy chuyến bay để giữ chỗ. Hãy kiểm tra lại mã chuyến bay."
        }

    # Nghiệp vụ: Chuyến bay hết chỗ
    if flight["available_seats"] <= 0:
        if _loi_te():
            return {"error": "seat unavailable"}
        return {
            "status": "error",
            "error": "seat_unavailable",
            "flight_no": flight["flight_no"],
            "available_seats": 0,
            "hint": "Chuyến bay đã hết chỗ hoàn toàn. Vui lòng chọn chuyến bay khác có số ghế khả dụng > 0."
        }

    # Giữ chỗ thành công: sinh mã booking_code
    BOOKING_COUNTER += 1
    carrier_prefix = flight["flight_no"][:2]
    booking_code = f"{carrier_prefix}-BK{BOOKING_COUNTER}"

    # Cập nhật số ghế khả dụng
    flight["available_seats"] -= 1

    now = time.time()
    booking_record = {
        "booking_code": booking_code,
        "flight_no": flight["flight_no"],
        "airline": flight["airline"],
        "passenger_name": str(passenger_name).strip(),
        "seat_code": seat_code,
        "depart_date": flight["depart_date"],
        "depart_time": flight["depart_time"],
        "arrive_time": flight["arrive_time"],
        "price": flight["base_price"],
        "refundable": flight["refundable"],
        "seat_class": flight["seat_class"],
        "state": "held",        # held -> confirmed
        "paid": False,
        "expires_in": "15m",
        "created_at": now,
        "expires_at": now + 15 * 60,
    }
    BOOKINGS_DATABASE[booking_code] = booking_record

    return {
        "status": "ok",
        "booking_code": booking_code,
        "flight_no": flight["flight_no"],
        "passenger_name": booking_record["passenger_name"],
        "seat_code": seat_code,
        "state": "held",
        "price": flight["base_price"],
        "refundable": flight["refundable"],
        "paid": False,
        "expires_in": "15m",
        "hint": "Giữ chỗ thành công. Cần gọi pay(booking_code, ...) trong vòng 15 phút để hoàn tất thanh toán."
    }


def pay(booking_code: str, payment_method: str = "credit_card") -> Dict[str, Any]:
    """Thực hiện thanh toán tiền thật cho mã giữ chỗ, chuyển trạng thái sang 'confirmed'.

    Tham số:
        booking_code: Mã đặt chỗ đã được cấp từ book_seat
        payment_method: Phương thức thanh toán (VD: 'credit_card', 'momo', 'bank_transfer')

    Trả về:
        Trạng thái thanh toán thành công và hóa đơn xác nhận vé.
    """
    b_code = str(booking_code).strip()
    booking = BOOKINGS_DATABASE.get(b_code)

    if not booking:
        if _loi_te():
            return {"error": "booking not found"}
        return {
            "status": "error",
            "error": "booking_not_found",
            "queried_booking_code": booking_code,
            "hint": "Mã đặt chỗ không tồn tại hoặc đã bị hủy do hết hạn giữ chỗ. Cần gọi book_seat trước."
        }

    # Kiểm tra thời gian sống của giữ chỗ (15 phút)
    if time.time() > booking.get("expires_at", float("inf")):
        booking["state"] = "expired"
        return {
            "status": "error",
            "error": "booking_expired",
            "booking_code": b_code,
            "hint": "Mã đặt chỗ đã hết hạn giữ chỗ (quá 15 phút). Vui lòng thực hiện giữ chỗ lại."
        }

    if booking["state"] == "confirmed" and booking["paid"]:
        return {
            "status": "ok",
            "booking_code": b_code,
            "flight_no": booking["flight_no"],
            "state": "confirmed",
            "paid": True,
            "amount": booking["price"],
            "note": "Booking này đã được thanh toán trước đó."
        }

    # Chuyển trạng thái sang confirmed
    booking["state"] = "confirmed"
    booking["paid"] = True
    booking["payment_method"] = payment_method

    return {
        "status": "ok",
        "booking_code": b_code,
        "flight_no": booking["flight_no"],
        "passenger_name": booking["passenger_name"],
        "state": "confirmed",
        "paid": True,
        "amount": booking["price"],
        "payment_method": payment_method,
        "depart_date": booking["depart_date"],
        "depart_time": booking["depart_time"],
        "hint": "Thanh toán thành công. Vé máy bay điện tử đã được xác nhận chính thức."
    }


def get_booking(booking_code: str) -> Dict[str, Any]:
    """Tra cứu thông tin trạng thái vé từ hệ thống cơ sở dữ liệu hàng không.

    Hàm này được dùng độc lập bởi Sensor Computational (Lớp 2 Harness)
    để đối chiếu chéo mà không phụ thuộc vào lời xưng của LLM.
    """
    b_code = str(booking_code).strip()
    booking = BOOKINGS_DATABASE.get(b_code)

    if not booking:
        return {
            "status": "error",
            "error": "booking_not_found",
            "booking_code": booking_code
        }

    return {
        "status": "ok",
        "booking": copy.deepcopy(booking)
    }


# ==============================================================================
# 3. ĐÓNG GÓI THÀNH DANH SÁCH TOOL TƯƠNG THÍCH LANGCHAIN / STANDALONE
# ==============================================================================

class StandaloneTool:
    """Wrapper công cụ chạy độc lập không phụ thuộc thư viện ngoài."""

    def __init__(self, func: Callable, name: Optional[str] = None, description: Optional[str] = None):
        self.func = func
        self.name = name or func.__name__
        self.description = description or (func.__doc__ or "").strip()

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def invoke(self, input_args: Any) -> str:
        """Thực thi tool theo chuẩn invoke của LangChain (trả về chuỗi JSON)."""
        if isinstance(input_args, dict):
            res = self.func(**input_args)
        elif isinstance(input_args, str):
            try:
                parsed = json.loads(input_args)
                if isinstance(parsed, dict):
                    res = self.func(**parsed)
                else:
                    res = self.func(input_args)
            except Exception:
                res = self.func(input_args)
        else:
            res = self.func(input_args)
        return json.dumps(res, ensure_ascii=False)


def get_flight_tools_list() -> List[Callable]:
    """Trả về danh sách 5 hàm nghiệp vụ nguyên bản."""
    return [search_flights, check_seat, book_seat, pay, get_booking]


def get_langchain_tools() -> List[Any]:
    """Đóng gói 5 tool cho LangChain agent.

    Nếu có thư viện langchain_core thì dùng decorator @tool,
    ngược lại dùng lớp StandaloneTool có giao diện tương đương.
    """
    try:
        from langchain_core.tools import tool
        return [
            tool(search_flights),
            tool(check_seat),
            tool(book_seat),
            tool(pay),
            tool(get_booking),
        ]
    except ImportError:
        return [
            StandaloneTool(search_flights),
            StandaloneTool(check_seat),
            StandaloneTool(book_seat),
            StandaloneTool(pay),
            StandaloneTool(get_booking),
        ]


if __name__ == "__main__":
    print("=== KIỂM THỬ ĐỘC LẬP MOCK_FLIGHT_TOOLS ===")
    reset_flight_database()

    # 1. Tìm chuyến bay
    res1 = search_flights("SGN", "DAD", "2026-10-07")
    print(f"1. search_flights: tìm thấy {res1.get('matched')} chuyến bay")

    # 2. Kiểm tra ghế VJ602 (hết chỗ) và VN122 (còn chỗ)
    res_vj = check_seat("VJ602")
    print(f"2a. check_seat(VJ602): available_seats={res_vj.get('available_seats')} (hết chỗ)")
    res_vn = check_seat("VN122")
    print(f"2b. check_seat(VN122): available_seats={res_vn.get('available_seats')}, price={res_vn.get('price')}đ")

    # 3. Giữ chỗ VN122
    res_book = book_seat("VN122", "Nguyen Van A", "14B")
    bcode = res_book.get("booking_code")
    print(f"3. book_seat(VN122): booking_code={bcode}, state={res_book.get('state')}")

    # 4. Thanh toán
    res_pay = pay(bcode, "credit_card")
    print(f"4. pay({bcode}): state={res_pay.get('state')}, paid={res_pay.get('paid')}")

    # 5. Sensor kiểm tra trực tiếp
    res_chk = get_booking(bcode)
    print(f"5. get_booking({bcode}): verified state={res_chk['booking']['state']}")
    print("=== HOÀN TẤT KIỂM THỬ CÔNG CỤ ===")
