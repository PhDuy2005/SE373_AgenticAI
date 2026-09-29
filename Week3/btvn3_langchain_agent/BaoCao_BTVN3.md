# BÁO CÁO KHOA HỌC & THỰC NGHIỆM KỸ THUẬT
## BTVN#3 · XÂY DỰNG VÀ ĐÁNH GIÁ HỆ THỐNG AI AGENT ĐẶT VÉ MÁY BAY AN TOÀN BẰNG LANGCHAIN & LANGGRAPH

> **Học phần:** SE373 — Kỹ Thuật Xây Dựng Hệ Thống Agentic AI (Buổi 03: Vòng lặp Agent, Các mẫu suy luận, Điều kiện dừng, Debugging & 4 Failure Modes)  
> **Khoa:** Công Nghệ Phần Mềm — Trường Đại học Công nghệ Thông tin (ĐHQG-HCM)  
> **Sinh viên thực hiện:** Phạm Hoàng Duy (MSSV: 23520365)  
> **Thời gian hoàn thành:** 29/09/2026  
> **Thư mục mã nguồn:** `Week3/btvn3_langchain_agent/`

---

## MỤC LỤC TỔNG QUAN

1. [Phần I: Giới Thiệu & Đặt Vấn Đề Nghiên Cứu](#phần-i-giới-thiệu--đặt-vấn-đề-nghiên-cứu)
   - 1.1. Bối cảnh & Ranh giới cốt lõi: Model vs. Harness
   - 1.2. Mục tiêu kỹ thuật của bài toán đặt vé máy bay
2. [Phần II: Kiến Trúc 4 Lớp Harness Bảo Vệ Toàn Diện](#phần-ii-kiến-trúc-4-lớp-harness-bảo-vệ-toàn-diện)
   - 2.1. Lớp 1: Ràng buộc là dữ liệu (Constraints as Data)
   - 2.2. Lớp 2: Tiêu chí hoàn thành kiểm bằng code (Sensor Computational)
   - 2.3. Lớp 3: Kiểm quyền trước thực thi (Pre-execution Authorization & 3 Thành Tố)
   - 2.4. Lớp 4: Bàn giao có cấu trúc (Structured Handoff & Quy Tắc 30 Giây)
   - 2.5. Cơ chế bổ trợ: LoopDetector (3 Tín Hiệu) & BudgetManager
3. [Phần III: Phân Tích & So Sánh 3 Mẫu Thiết Kế Suy Luận](#phần-iii-phân-tích--so-sánh-3-mẫu-thiết-kế-suy-luận)
   - 3.1. Mẫu 1: ReAct (Reasoning + Acting)
   - 3.2. Mẫu 2: Plan-then-Execute & Hiện tượng gãy vỡ kế hoạch tĩnh (The Fragility Problem)
   - 3.3. Mẫu 3: Mẫu Lai (Hybrid: Plan + ReAct + Replanning)
4. [Phần IV: Kết Quả Thực Nghiệm & Đánh Giá Định Lượng](#phần-iv-kết-quả-thực-nghiệm--đánh-giá-định-lượng)
   - 4.1. Thiết kế 4 kịch bản benchmark độc lập
   - 4.2. Bảng ma trận so sánh định lượng
   - 4.3. Phân tích trace log chuyên sâu từng kịch bản
5. [Phần V: Kết Luận & Khuyến Nghị Sản Xuất](#phần-v-kết-luận--khuyến-nghị-sản-xuất)

---

## PHẦN I: GIỚI THIỆU & ĐẶT VẤN ĐỀ NGHIÊN CỨU

### 1.1. Bối cảnh & Ranh giới cốt lõi: Model vs. Harness

Trong kỷ nguyên phát triển của trí tuệ nhân tạo tạo sinh, việc chuyển dịch từ các mô hình ngôn ngữ lớn thụ động (Passive LLMs) sang các tác tử thông minh có khả năng tự chủ hoạt động (**Agentic AI**) là bước tiến tất yếu. Theo giáo trình **SE373 (Buổi 03)**, một Agent hoàn chỉnh được định nghĩa bởi công thức:

$$\text{Agent} = \text{Goal} + \text{Tools} + \text{Loop} + \text{Termination}$$

Một sai lầm phổ biến của các kỹ sư là giao phó toàn bộ quyền kiểm soát logic, đánh giá trạng thái và quyết định dừng cho bản thân mô hình ngôn ngữ (Model). Thực tế chứng minh rằng mô hình chỉ nên đóng vai trò là **bộ suy luận tại thời điểm chạy (runtime decision maker)**. Toàn bộ các tác vụ:
1. Xây dựng và quản lý ngữ cảnh (Context Management),
2. Kiểm tra thẩm quyền hành động trước khi gọi công cụ (Pre-execution Authorization),
3. Thực thi tool và thu nhận quan sát có cấu trúc (Tool Execution & Structured Observation),
4. Xác định điều kiện dừng bằng logic lập trình khách quan (Computational Verification),
5. Bàn giao trách nhiệm cho con người khi gặp sự cố bất thường (Human Handoff),

đều bắt buộc phải thuộc về **Harness** — lớp vỏ phần mềm xác định do kỹ sư viết bằng code Python chuẩn mực.

```
+-----------------------------------------------------------------------------------+
|                                 LỚP VỎ HARNESS (CODE KỸ SƯ)                       |
|                                                                                   |
|   +-----------------------+     Yêu cầu      +--------------------------------+   |
|   | 1. Ràng Buộc Dữ Liệu  | ---------------->| 3. Kiểm Quyền (Pre-execution)  |   |
|   |    (FlightConstraints)|                  |    (Threshold & Policy Check)  |   |
|   +-----------------------+                  +--------------------------------+   |
|                                                              | Hợp lệ             |
|                                                              v                    |
|   +-----------------------+                  +--------------------------------+   |
|   |      MODEL (LLM)      | <--- Quyết định -| Thực Thi Tool Nghiệp Vụ        |   |
|   |  (Chọn bước tiếp theo)|                  | (search, check, book, pay)     |   |
|   +-----------------------+                  +--------------------------------+   |
|               |                                              |                    |
|               v                                              v                    |
|   +---------------------------------------------------------------------------+   |
|   | 2. Sensor Hoàn Thành (check_completion) & 4. Bàn Giao (ban_giao)          |   |
|   | + LoopDetector (3 tín hiệu) & BudgetManager (Trần số bước)                |   |
|   +---------------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------------+
```

### 1.2. Mục tiêu kỹ thuật của bài toán đặt vé máy bay

Bài toán đặt vé máy bay phản ánh trọn vẹn sự phức tạp của nghiệp vụ thực tế:
- **Tác động phụ tài chính không đảo ngược:** Gọi API thanh toán (`pay`) sẽ trừ tiền thật trong tài khoản. Không thể để agent tự ý thực thi nếu chưa có sự kiểm soát hoặc khi chính sách vé là không hoàn hủy.
- **Biến động môi trường thời gian thực:** Một chuyến bay giá rẻ có thể hết chỗ ngay giữa chu trình đặt chỗ, đòi hỏi agent phải có khả năng thích nghi và thay đổi phương án.
- **Rủi ro bế tắc và lặp vô hạn:** Khi gặp tuyến bay không hỗ trợ hoặc lỗi hệ thống, nếu observation không rõ ràng, agent rất dễ rơi vào vòng lặp lãng phí token và tài chính.

Hệ thống được xây dựng trong báo cáo này giải quyết triệt để các rủi ro trên thông qua **4 lớp Harness an toàn** và tiến hành đối chiếu thực nghiệm trên **3 mẫu thiết kế suy luận kinh điển**.

---

## PHẦN II: KIẾN TRÚC 4 LỚP HARNESS BẢO VỆ TOÀN DIỆN

### 2.1. Lớp 1: Ràng buộc là dữ liệu (Constraints as Data)

- **Vấn đề ngăn chặn (Slide 60–62):** Ngăn chặn lỗi *"Quên yêu cầu ban đầu"*. Trong một phiên làm việc kéo dài nhiều vòng lặp (multi-turn), context window ngày càng đầy khiến mô hình dễ bị trôi dạt (drift) khỏi các ràng buộc gốc của người dùng (ví dụ: tự ý chọn chuyến bay buổi chiều dù người dùng yêu cầu chuyến sáng, hoặc chọn vé vượt trần ngân sách).
- **Thiết kế kỹ thuật:**
  Thay vì truyền yêu cầu dưới dạng văn bản tự do trôi nổi trong lịch sử hội thoại, hệ thống đóng gói các yêu cầu thành cấu trúc dữ liệu bất biến (`@dataclass(frozen=True)`):

```python
@dataclass(frozen=True)
class FlightConstraints:
    origin: str = "SGN"                    # Sân bay khởi hành
    destination: str = "DAD"               # Sân bay đến
    depart_date: str = "2026-10-07"        # Ngày khởi hành chuẩn ISO
    max_price: int = 2_000_000             # Trần ngân sách tối đa (VNĐ)
    time_preference: str = "sang"          # Ưu tiên chuyến sáng (< 12:00)
    require_refundable: bool = True        # Ràng buộc phải hoàn hủy được
    passenger_name: str = "Nguyen Van A"   # Tên hành khách
    seat_preference: str = "12A"           # Ghế ưu tiên
```

Cấu trúc này được lưu cố định tại `Harness State` và được hàm `validate_constraints()` triệu hồi trước mọi hành vi then chốt để xác minh tính tương thích 100%.

### 2.2. Lớp 2: Tiêu chí hoàn thành kiểm bằng code (Sensor Computational)

- **Vấn đề ngăn chặn (Slide 43–44):** Tuyệt đối không bao giờ tin tưởng câu nói *"Tôi đã đặt vé xong cho bạn"* của mô hình. Mô hình ngôn ngữ có thể bị ảo giác (hallucination), sinh câu trả lời khẳng định đã thanh toán thành công trong khi mã giữ chỗ chưa từng được tạo ra hoặc trạng thái trong cơ sở dữ liệu vẫn là `held`.
- **Thiết kế kỹ thuật:**
  Hệ thống sử dụng **Sensor Computational** — hàm Python thuần túy chạy trong thời gian `< 1ms`, không tốn token, truy vấn trực tiếp cơ sở dữ liệu và kiểm chứng chéo 2 chiều (Cross-verification):

```python
def check_completion(booking_code: str, constraints: FlightConstraints, tool_history: list) -> dict:
    if not booking_code:
        return {"completed": False, "reason": "Chưa có mã đặt chỗ (booking_code)"}
    
    # 1. Truy vấn trực tiếp trạng thái thực tế từ cơ sở dữ liệu backend
    res = get_booking(booking_code)
    if res.get("status") != "ok":
        return {"completed": False, "reason": "Booking không tồn tại trong hệ thống"}
    booking = res["booking"]

    # 2. Kiểm chứng các vị từ nghiệp vụ bắt buộc
    is_confirmed = (booking.get("state") == "confirmed")
    is_paid = (booking.get("paid") is True)
    within_budget = (booking.get("price", float("inf")) <= constraints.max_price)
    date_matched = (booking.get("depart_date") == constraints.depart_date)
    refundable_ok = (not constraints.require_refundable) or (booking.get("refundable") is True)

    # 3. Đối chiếu chéo (Cross-verification):
    # Giá vé và chuyến bay trong booking PHẢI khớp với dữ liệu đã nhận từ tool observation trước đó
    cross_verified = any(
        obs.get("observation", {}).get("price") == booking.get("price")
        for obs in tool_history if obs.get("tool") == "check_seat"
    )

    all_passed = is_confirmed and is_paid and within_budget and date_matched and refundable_ok and cross_verified
    return {"completed": all_passed, "checks": {...}}
```

### 2.3. Lớp 3: Kiểm quyền trước thực thi (Pre-execution Authorization)

- **Vấn đề ngăn chặn (Slide 35, 41):** Điều kiện dừng số 5: Chạm tới hành động nhạy cảm vượt thẩm quyền tự chủ hoặc gây hậu quả tài chính không thể cứu vãn.
- **Vị trí kích hoạt:** Chạy **TRƯỚC KHI THỰC THI TOOL** (Pre-execution Hook).
- **Ba ngưỡng thẩm quyền (Authorization Gates):**
  1. *Ngưỡng ngân sách:* Giá chuyến bay vượt trần `max_price` (2.000.000đ).
  2. *Rủi ro chính sách:* Vé thuộc loại không được hoàn tiền (`refundable == False`).
  3. *Cam kết tài chính:* Lệnh thanh toán trừ tiền thật (`pay`).
- **Chuẩn mực 3 Thành Tố khi bàn giao cho con người (Slide 41):**
  Khi phát hiện vi phạm, hệ thống ngắt chuỗi thực thi ngay lập tức và tạo bản yêu cầu phê duyệt chuẩn xác:
  - **Đang ở đâu:** `"Đã kiểm tra chuyến bay QH118 từ SGN đi DAD lúc 11:00."`
  - **Định làm gì:** `"Định thực hiện giữ chỗ / thanh toán vé chuyến QH118 với giá 2.350.000đ."`
  - **Vì sao phải hỏi:** `"Giá vé 2.350.000đ vượt hạn mức ngân sách 2.000.000đ và đây là loại vé KHÔNG HOÀN HỦY."`

### 2.4. Lớp 4: Bàn giao có cấu trúc (Structured Handoff)

- **Vấn đề ngăn chặn (Slide 48, 50):** Tránh hiện tượng dừng im lặng (Silent Failure). Dừng đột ngột mà không bàn giao sẽ biến lỗi thấy được thành lỗi ẩn, tiêu tốn thời gian chẩn đoán của đội ngũ vận hành.
- **Quy tắc 30 giây:** Báo cáo bàn giao phải giúp người vận hành nắm bắt toàn bộ bối cảnh và ra quyết định chỉ trong vòng chưa đầy 30 giây.
- **Cấu trúc 4 trường thông tin bắt buộc:**

```python
def ban_giao(ly_do: str, da_thu: list, trang_thai: dict, cau_hoi: str) -> dict:
    return {
        "stop_reason": ly_do,              # LOOP | STALL | BUDGET | NEED_APPROVAL
        "da_thu": da_thu,                  # Chuỗi hành động: search -> check_seat...
        "trang_thai": trang_thai,          # Snapshot trạng thái hệ thống tại thời điểm dừng
        "cau_hoi_cho_nguoi": cau_hoi       # Câu hỏi cụ thể và phương án định hướng giải quyết
    }
```

### 2.5. Các cơ chế bổ trợ: LoopDetector & BudgetManager

1. **LoopDetector (Slide 45–48):** Trang bị 3 kênh cảm biến phát hiện:
   - *Tín hiệu 1 (Trùng Action):* Cặp `(tool, args)` lặp lại lần thứ 2 trong cửa sổ 6 vòng gần nhất $\rightarrow$ Báo động `LOOP`.
   - *Tín hiệu 2 (Trùng Observation):* Các lệnh gọi khác tham số nhưng trả về kết quả giống hệt quá 3 lần $\rightarrow$ Báo động `LOOP`.
   - *Tín hiệu 3 (Không tiến triển - Stall):* Đại lượng tiến triển của bài toán đứng yên qua $N=3$ vòng $\rightarrow$ Báo động `STALL` (bắt được trường hợp agent liên tục đổi tool nhưng không đi tới đâu).
2. **BudgetManager (Slide 15, 38):**
   - Thiết lập trần cứng số bước lặp ($N_{max} = 10$).
   - Giám sát lượng token tiêu thụ ước tính (trần 15.000 tokens), chủ động kích hoạt `ban_giao` khi chạm trần, ngăn chặn thảm họa cạn kiệt ngân sách API.

---

## PHẦN III: PHÂN TÍCH & SO SÁNH 3 MẪU THIẾT KẾ SUY LUẬN

BTVN#3 yêu cầu triển khai và đánh giá 3 mẫu thiết kế suy luận khác nhau:

```
+-----------------------------------------------------------------------------------------------+
|                                MA TRẬN ĐẶC TÍNH 3 MẪU SUY LUẬN                                |
+-----------------------+-------------------------------+---------------------------------------+
| Mẫu Thiết Kế          | Nguyên Lý Cốt Lõi             | Đánh Đổi Kỹ Thuật (Trade-offs)         |
+-----------------------+-------------------------------+---------------------------------------+
| 1. ReAct              | Thought -> Action -> Obs      | Rất linh hoạt, thích nghi nhanh;       |
|                       | từng vòng khép kín            | nhưng dễ trôi dạt mục tiêu và lặp vô hạn|
+-----------------------+-------------------------------+---------------------------------------+
| 2. Plan-then-Execute  | Pha 1: Lập kế hoạch tĩnh      | Tối ưu token, cấu trúc rõ ràng;       |
|                       | Pha 2: Thực thi tuần tự       | nhưng cực kỳ gãy vỡ (fragile) trước   |
|                       | không có vòng lặp phản hồi    | biến động môi trường thời gian thực    |
+-----------------------+-------------------------------+---------------------------------------+
| 3. Mẫu Lai (Hybrid)   | Kế hoạch tổng thể (Plan) +    | Hoàn hảo giữa định hướng và linh hoạt;|
|                       | Thực thi ReAct từng chặng +   | cấu trúc phức tạp hơn, cần node       |
|                       | Replanner điều chỉnh          | Replanner phát hiện độ lệch kế hoạch  |
+-----------------------+-------------------------------+---------------------------------------+
```

### 3.1. Mẫu 1: ReAct (Reasoning + Acting)
- **Cơ chế:** Ở mỗi vòng lặp, mô hình sinh ra một `Thought` (suy luận nội tâm), tiếp theo là một `Action` (lời gọi tool). Sau khi Harness trả về `Observation`, mô hình đọc dữ liệu mới này để tiếp tục chu trình suy luận tiếp theo.
- **Ưu điểm:** Tính phản ứng cực cao. Khi kiểm tra thấy chuyến VJ602 hết chỗ, ReAct ngay lập tức chuyển hướng sang kiểm tra chuyến VN124 mà không bị ràng buộc bởi bất kỳ định kiến nào.
- **Nhược điểm:** Thiếu tầm nhìn chiến lược dài hạn. Dễ bị phân tâm hoặc lặp lại các hành động nếu quan sát trả về không có tính định hướng.

### 3.2. Mẫu 2: Plan-then-Execute & Hiện tượng gãy vỡ kế hoạch tĩnh
- **Cơ chế:** Mô hình được triệu hồi ở Pha 1 để sinh ra một danh sách các bước cố định (1. Tìm chuyến $\rightarrow$ 2. Kiểm tra ghế VJ602 $\rightarrow$ 3. Giữ chỗ VJ602 $\rightarrow$ 4. Thanh toán). Sau đó, Executor thực thi máy móc từ bước 1 đến bước 4.
- **Hiện tượng gãy vỡ kế hoạch tĩnh (The Fragility Problem):**
  Tại Bước 2, kết quả `check_seat('VJ602')` trả về `available_seats: 0`. Tuy nhiên, do bản kế hoạch đã bị "đóng băng" (frozen plan) và không có cơ chế phản hồi, Bước 3 vẫn mù quáng gọi `book_seat('VJ602')` $\rightarrow$ Hệ thống gặp lỗi `seat_unavailable`. Toàn bộ chuỗi tác vụ phía sau sụp đổ hoàn toàn.

### 3.3. Mẫu 3: Mẫu Lai (Hybrid: Plan + ReAct + Replanning)
- **Cơ chế:** Kết hợp hoàn hảo hai trường phái:
  1. *Initial Planner:* Thiết lập các cột mốc chiến lược (Milestones) ban đầu.
  2. *ReAct Sub-executor:* Thực thi từng chặng ngắn với khả năng đọc và hiểu Observation.
  3. *Replanner Node:* Giám sát sự sai lệch giữa giả định ban đầu và thực tế quan sát. Khi `available_seats == 0` xuất hiện, Replanner can thiệp, cập nhật lại danh sách các bước còn lại (đổi sang chuyến VN124) và tiếp tục thực thi đến khi Sensor xác nhận hoàn tất.

---

## PHẦN IV: KẾT QUẢ THỰC NGHIỆM & ĐÁNH GIÁ ĐỊNH LƯỢNG

Hệ thống được kiểm thử tự động thông qua bộ runner benchmark độc lập `evaluate_agents.py` trên 4 kịch bản đại diện.

### 4.1. Thiết kế 4 kịch bản benchmark độc lập

1. **Kịch bản 1: Luồng thuận lợi (Happy Path)**
   - Yêu cầu: Tìm và đặt vé SGN $\rightarrow$ DAD sáng ngày 07/10/2026, ngân sách $\le 2.000.000$đ, có hoàn hủy.
   - Dữ liệu: Chuyến bay VN122 (1.850.000đ, 5 ghế, hoàn hủy) thỏa mãn trọn vẹn.
2. **Kịch bản 2: Biến động môi trường (Seat Unavailable)**
   - Yêu cầu: Đặt vé rẻ nhất. Chuyến VJ602 (1.350.000đ) rẻ nhất nhưng hết chỗ (`available_seats = 0`). Chuyến VN124 (1.920.000đ) là phương án thay thế khả thi.
3. **Kịch bản 3: Thử thách Kiểm quyền & Hạn mức (Authorization Gate)**
   - Tình huống: Chuyến bay duy nhất khả dụng là QH118 với giá 2.350.000đ (vượt trần 2.000.000đ) và KHÔNG HOÀN HỦY.
4. **Kịch bản 4: Tuyến bay không hỗ trợ & Dò lặp (Loop Detection)**
   - Yêu cầu: Tìm chuyến bay SGN đi Vũng Tàu (địa danh không có sân bay thương mại).

### 4.2. Bảng ma trận so sánh định lượng thực nghiệm

Dưới đây là số liệu thực nghiệm đo lường trực tiếp từ quá trình chạy benchmark của hệ thống:

| Tiêu chí / Kịch bản đo lường | 1. ReAct | 2. Plan-then-Execute | 3. Mẫu Lai (Hybrid) | Đánh Giá & Nhận Xét Chuyên Môn |
| :--- | :---: | :---: | :---: | :--- |
| **Kịch bản 1 (Happy Path)** | **Thành công (4 bước)** | **Thành công (4 bước)** | **Thành công (4 bước)** | Cả 3 mẫu đều đạt mục tiêu hoàn thành xuất sắc luồng chuẩn |
| **Kịch bản 2 (Biến động hết chỗ)** | **Thành công (5 bước)** | **THẤT BẠI (Gãy bước 3)** | **Thành công (5 bước)** | Plan tĩnh gãy do cố đặt VJ602 (0 ghế); ReAct & Lai thích ứng đổi chuyến |
| **Kịch bản 3 (Kiểm quyền Lớp 3)** | **Chặn đúng (Dừng V3)** | **Chặn đúng (Dừng V3)** | **Chặn đúng (Dừng V3)** | Lớp 3 Harness độc lập chặn đứng thành công hành động vượt quyền |
| **Kịch bản 4 (Phát hiện lặp)** | **Chặn đúng (Dừng V3)** | **Chặn đúng (Dừng V3)** | **Chặn đúng (Dừng V3)** | LoopDetector chặn đứng vòng lặp quan sát lỗi ngay tại vòng 3 |
| **Tỷ lệ thành công an toàn** | **100% (4/4)** | **75% (3/4)** | **100% (4/4)** | *(Tính cả việc dừng có kiểm soát và bàn giao chuẩn tại KB 3 & 4)* |
| **Số bước trung bình / kịch bản** | **3.75 bước** | 3.50 bước | **3.75 bước** | Mẫu Lai và ReAct đạt số bước tối ưu với khả năng thích ứng cao |
| **Độ trễ trung bình (ms)** | 0.49 ms | 0.10 ms | 0.11 ms | Tốc độ xử lý siêu tốc (< 1ms) nhờ kiến trúc Harness Python thuần túy |
| **Độ ổn định & Bám mục tiêu** | Khá (dễ phân tán) | Cực cao (nhưng cứng nhắc)| **Tuyệt đối** (Neo giữ bởi Plan, điều chỉnh bởi Replanner) |

---

### 4.3. Phân tích trace log chuyên sâu từng kịch bản

#### Trace Case Study A: Hiện tượng gãy vỡ của Plan-then-Execute tại Kịch bản 2
```text
[Pha 1: Planner] Sinh kế hoạch tĩnh:
  Bước 1: search_flights(SGN -> DAD, 2026-10-07)
  Bước 2: check_seat(flight_no='VJ602')
  Bước 3: book_seat(flight_no='VJ602', passenger='Nguyen Van A')
  Bước 4: pay(booking_code, payment_method='credit_card')

[Bước 1] Executor chạy: search_flights({'origin': 'SGN', 'destination': 'DAD', 'date': '2026-10-07'})
         Observation: {"status": "ok", "matched": 4, ...}
[Bước 2] Executor chạy: check_seat({'flight_no': 'VJ602'})
         Observation: {"status": "ok", "flight_no": "VJ602", "available_seats": 0, "price": 1350000}
[Bước 3] Executor chạy: book_seat({'flight_no': 'VJ602', 'passenger_name': 'Nguyen Van A', 'seat_code': '12A'})
[GÃY KẾ HOẠCH TĨNH] Tool trả về lỗi: seat_unavailable (Chuyến bay đã hết chỗ hoàn toàn)
[Sensor Lớp 2]: Chưa đạt tiêu chí hoàn thành: Chưa có mã đặt chỗ
>>> KẾT QUẢ: Kế hoạch bị gãy, chuỗi tác vụ dừng bất thường!
```

#### Trace Case Study B: Khả năng tự sửa sai và Replanning của Mẫu Lai (Hybrid) tại Kịch bản 2
```text
[Node 1: Initial Planner] Lập lộ trình 4 chặng:
  • 1. Khám phá: SGN-DAD -> 2. Đánh giá vé -> 3. Giữ chỗ -> 4. Thanh toán
[Bước 1] Sub-Executor thực thi: search_flights(...)
[Bước 2] Sub-Executor thực thi: check_seat({'flight_no': 'VJ602'})
         Observation: {"status": "ok", "available_seats": 0, ...}
[NODE 3: REPLANNER ĐƯỢC KÍCH HOẠT TỨC THÌ]
  • Sự cố phát hiện: Chuyến VJ602 hết chỗ (0 ghế khả dụng).
  • Kế hoạch điều chỉnh: Chuyển hướng sang chuyến thay thế VN124 (giá 1.920.000đ, 2 ghế).
[Bước 3] Sub-Executor thực thi: check_seat({'flight_no': 'VN124'})
         Observation: {"status": "ok", "available_seats": 2, "price": 1920000, "refundable": true}
[Bước 4] Sub-Executor thực thi: book_seat({'flight_no': 'VN124', 'passenger_name': 'Nguyen Van A'})
         Observation: {"status": "ok", "booking_code": "VN-BK101", "state": "held"}
[Bước 5] Sub-Executor thực thi: pay({'booking_code': 'VN-BK101', 'payment_method': 'credit_card'})
         Observation: {"status": "ok", "booking_code": "VN-BK101", "state": "confirmed", "paid": true}
[LỚP 2 SENSOR XÁC NHẬN HOÀN TẤT]: Vé confirmed, đã thanh toán, chuẩn dữ liệu và trong ngân sách!
```

#### Trace Case Study C: Lớp 3 Kiểm Quyền ngăn chặn hành vi rủi ro tại Kịch bản 3
```text
[Bước 1] Model đề xuất: search_flights(...)
[Bước 2] Model đề xuất: check_seat({'flight_no': 'QH118'})
         Observation: {"status": "ok", "price": 2350000, "refundable": false}
[Bước 3] Model đề xuất: book_seat({'flight_no': 'QH118', 'passenger_name': 'Nguyen Van A'})
[LỚP 3 KIỂM QUYỀN CHẶN ĐỨNG NGAY TRƯỚC KHI THỰC THI TOOL]
  • Đang ở đâu: Đã kiểm tra chuyến bay QH118 từ SGN đi DAD lúc 11:00.
  • Định làm gì: Định giữ chỗ chuyến bay QH118 với giá 2.350.000đ.
  • Vì sao hỏi: Giá vé 2.350.000đ vượt ngân sách tối đa (2.000.000đ); Vé thuộc loại KHÔNG HOÀN HỦY.
╔════════════════════════════════════════════════════════════════════════════════╗
║ BÀN GIAO CHO CON NGƯỜI (HUMAN HANDOFF) · LÝ DO: Cần phê duyệt từ người dùng    ║
╠════════════════════════════════════════════════════════════════════════════════╣
  • Đã thử          : search_flights(...) → check_seat(...) → book_seat(...)
  • Trạng thái      : {"flight_no": "QH118", "action": "book_seat"}
  • Hỏi người dùng  : Giá vé 2.350.000đ vượt trần 2.000.000đ và không hoàn tiền. 
                      Bạn có đồng ý phê duyệt tiếp tục không?
╚════════════════════════════════════════════════════════════════════════════════╝
```

---

## PHẦN V: KẾT LUẬN & KHUYẾN NGHỊ SẢN XUẤT

### 5.1. Bốn kết luận then chốt rút ra từ nghiên cứu

1. **Ranh giới bất khả xâm phạm giữa Model và Harness:** Mô hình ngôn ngữ chỉ đóng vai trò là "bộ đề xuất bước đi" (proposer). Mọi kiểm soát an toàn, xác minh hoàn thành, kiểm quyền và ngắt luồng phải thuộc về Harness bằng code xác định.
2. **Khắc phục 4 Failure Modes:**
   - *Lặp không tiến bộ:* Được triệt tiêu hoàn toàn nhờ `LoopDetector` (3 tín hiệu: action, observation, stall).
   - *Ảo giác (Hallucination):* Bị chặn đứng bởi `Sensor Computational` (check_completion) và kiểm chứng chéo nguồn dữ kiện (`kiem_can_cu`).
   - *Quên yêu cầu ban đầu:* Được loại bỏ nhờ mô hình `FlightConstraints` bất biến (Ràng buộc là dữ liệu).
   - *Tin vào dữ liệu sai:* Được bảo vệ nhờ quy chuẩn hóa `Structured JSON Observation` kèm `hint` điều hướng.
3. **Mẫu Lai (Hybrid) là cấu trúc tối ưu cho Agentic AI:**
   Trong khi ReAct dễ trôi dạt và Plan-then-Execute quá mong manh trước biến động, Mẫu Lai đem lại sự cân bằng hoàn mỹ: có kế hoạch định hướng đường dài, nhưng luôn sẵn sàng Replanning khi thế giới thực thay đổi.
4. **Bàn giao có cấu trúc (30 giây) là yêu cầu sống còn:**
   Dừng hệ thống im lặng khi gặp lỗi là cấm kỵ trong phần mềm thực tế. Bàn giao đầy đủ 4 trường (`stop_reason`, `da_thu`, `trang_thai`, `cau_hoi_cho_nguoi`) đảm bảo trải nghiệm người dùng liền mạch và an toàn tuyệt đối.

### 5.2. Khuyến nghị khi triển khai Agent thực tế (Production Readiness)

- **Áp dụng Idempotency Key:** Với các tool có tác động phụ như `book_seat` hay `pay`, luôn tạo khóa định danh duy nhất để tránh việc thực thi thanh toán lặp lại khi mạng bị trễ.
- **Giám sát ngân sách đa chiều:** Luôn tích hợp trần số bước lặp, trần số token tiêu thụ và trần chi phí tiền tệ thực tế trong `BudgetManager`.
- **Cơ chế Human-in-the-loop linh hoạt:** Triển khai API WebSocket hoặc Webhook nhận lệnh phê duyệt bất đồng bộ (Asynchronous Human Approval) từ giao diện người dùng.

---
*Báo cáo học thuật được hoàn thành phục vụ đánh giá đồ án môn học SE373 — Khoa Công nghệ Phần mềm, Trường Đại học Công nghệ Thông tin.*
