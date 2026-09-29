# BTVN#3 · Dựng Agent Đặt Vé Máy Bay bằng LangChain & LangGraph
> **Học phần:** SE373 — Kỹ thuật xây dựng hệ thống Agentic AI (Buổi 03: Agent Fundamentals)  
> **Khoa Công nghệ Phần mềm — Trường Đại học Công nghệ Thông tin (UIT)**  
> **Tác giả:** Sinh viên thực hiện theo đề cương môn học  

---

## 📌 1. Giới Thiệu Tổng Quan

Dự án này là giải pháp kỹ thuật hoàn chỉnh cho **Bài tập về nhà số 3 (BTVN#3)**, tập trung vào việc hiện thực hóa một hệ thống **AI Agent hỗ trợ tìm kiếm và đặt vé máy bay** có khả năng tự chủ hoạt động, xử lý nghiệp vụ thực tế qua các công cụ mô phỏng (Mockup Tools), được bao bọc an toàn bởi **bộ Harness 4 lớp bảo vệ** và cài đặt so sánh thực nghiệm trên **3 mẫu thiết kế suy luận** khác nhau.

### Yêu cầu bài tập (Theo `Week3-requirment.md`):
1. **Đủ các lớp Harness:**
   - Ràng buộc là dữ liệu (*Constraints as Data*)
   - Tiêu chí hoàn thành kiểm bằng code (*Sensor Computational*)
   - Kiểm quyền (*Pre-execution Authorization*)
   - Bàn giao có cấu trúc (*Structured Handoff*)
2. **Cài đặt Agent với 3 mẫu thiết kế suy luận:**
   - **ReAct** (Reasoning + Acting)
   - **Plan-then-Execute** (Lập kế hoạch rồi thực thi)
   - **Mẫu Lai** (Hybrid: Plan + ReAct + Replanning)
3. **Đánh giá hiệu quả thực nghiệm:**
   - Đo lường định lượng trên 4 kịch bản thực tế.
   - Nộp mã nguồn `.py` kèm báo cáo định dạng `.md` và `.html`.

---

## 🏗️ 2. Kiến Trúc Hệ Thống (Architecture)

```
                            [Người Dùng (Human Request)]
                                         │
                                         ▼
                     [LỚP 1: Ràng Buộc Là Dữ Liệu (Constraints)]
                                         │
                     ┌───────────────────┴───────────────────┐
                     │           VÒNG LẶP AGENT LOOP         │
                     │                                       │
                     │  ┌─────────────────────────────────┐  │
                     │  │ Model Suy Luận (ReAct/Plan/Lai) │  │
                     │  └────────────────┬────────────────┘  │
                     │                   │ tool_call         │
                     │                   ▼                   │
                     │  ┌─────────────────────────────────┐  │
                     │  │   LỚP 3: KIỂM QUYỀN TRƯỚC THỰC  │  │
                     │  │   THI (Pre-execution AuthHook)  │  │
                     │  └────────┬────────────────────────┘  │
                     │           │                           │
                     │           ├─[Vượt quyền / Cần duyệt]──┼───► [LỚP 4: Bàn Giao (Handoff)]
                     │           │                           │
                     │           ▼ [Hợp lệ]                  │
                     │  ┌─────────────────────────────────┐  │
                     │  │  Mockup Tools (JSON Observation)│  │
                     │  └────────────────┬────────────────┘  │
                     │                   │ observation       │
                     │                   ▼                   │
                     │  ┌─────────────────────────────────┐  │
                     │  │ LỚP 2: Tiêu Chí Hoàn Thành Bằng │  │
                     │  │ Code (Sensor Computational)     │  │
                     │  └────────┬────────────────────────┘  │
                     │           │                           │
                     │           ├─[Đạt mục tiêu]────────────┼───► [Hoàn Tất Thành Công]
                     │           │                           │
                     │           ▼ [Chưa xong]               │
                     │  ┌─────────────────────────────────┐  │
                     │  │ LoopDetector & BudgetManager    │  │
                     │  └────────┬────────────────────────┘  │
                     │           │                           │
                     │           ├─[Lặp / Bế tắc / Hết hạn]──┼───► [LỚP 4: Bàn Giao (Handoff)]
                     │           │                           │
                     │           ▼ [Bình thường]             │
                     │      (Lặp vòng kế)                    │
                     └───────────────────────────────────────┘
```

### Chi tiết 4 Lớp Harness (Slide 10–15, 34–49, 62):
1. **Lớp 1: Ràng buộc là dữ liệu (`FlightConstraints`):** Lưu trữ độc lập tiêu chí ngày bay, giờ bay, trần giá, yêu cầu hoàn hủy dưới dạng `@dataclass(frozen=True)` bất biến. Ngăn chặn hiện tượng *Quên yêu cầu ban đầu (Failure Mode 3)* khi lịch sử hội thoại dài ra.
2. **Lớp 2: Tiêu chí hoàn thành kiểm bằng code (`check_completion`):** Sensor computational độc lập với mô hình. Truy vấn trực tiếp trạng thái database (`get_booking`), kiểm tra 6 vị từ logic (`status == "confirmed"`, `paid == True`, `price <= max_price`, v.v.) và đối chiếu chéo giá vé (*Cross-verification*). Ngăn chặn hiện tượng *Bịa đặt thông tin (Failure Mode 2)*.
3. **Lớp 3: Kiểm quyền trước khi thực thi (`PreExecutionAuthHook`):** Chạy trước khi thực thi tool nhạy cảm. Chặn đứng các tool ngoài whitelist, các giao dịch giữ chỗ/thanh toán vượt trần ngân sách hoặc vé thuộc diện *Không hoàn hủy*. Xuất thông báo hỏi duyệt đủ 3 yếu tố: *Đang ở đâu*, *Định làm gì*, *Vì sao phải hỏi*.
4. **Lớp 4: Bàn giao có cấu trúc (`ban_giao`):** Dừng có kiểm soát kèm cấu trúc 4 trường bắt buộc (`stop_reason`, `da_thu`, `trang_thai`, `cau_hoi_cho_nguoi`), tuân thủ *quy tắc 30 giây* giúp con người can thiệp tức thì. Loại bỏ hoàn toàn lỗi dừng im lặng (*Silent Crash*).
5. **Cơ chế bổ trợ:**
   - **`LoopDetector`:** Dò 3 tín hiệu độc lập: trùng Action $k=2$, trùng Observation $k_{obs}=3$, và bế tắc tiến triển Stall $n=3$ (Slide 45–48).
   - **`BudgetManager`:** Khóa trần cứng số bước ($N_{max}=10$) và token để ngăn runaway cost (Slide 15, 38).

---

## 📂 3. Cấu Trúc Thư Mục Mã Nguồn

```
d:\DoAn\AgenticAI\Week3\btvn3_langchain_agent\
│
├── requirements.txt           # Danh mục thư viện phụ thuộc (langchain, langgraph, pydantic, v.v.)
├── .env.example               # Mẫu cấu hình biến môi trường và API key
├── README.md                  # Hướng dẫn chi tiết dự án (file này)
│
├── mock_flight_tools.py       # Dữ liệu tĩnh + 5 tools mockup chuẩn JSON Observation
├── flight_harness.py          # Đủ 4 Lớp Harness + LoopDetector + BudgetManager
├── model_provider.py          # MockBookingModel (deterministic) & ModelThat (kết nối LLM thật)
│
├── agent_react.py             # Cài đặt Agent theo mẫu thiết kế ReAct
├── agent_plan_execute.py      # Cài đặt Agent theo mẫu thiết kế Plan-then-Execute
├── agent_hybrid.py            # Cài đặt Agent theo mẫu thiết kế Lai (Plan + ReAct + Replanner)
│
├── evaluate_agents.py         # Runner thực thi ma trận Benchmark 12 lượt qua 4 kịch bản
├── main.py                    # Giao diện dòng lệnh (CLI) tương tác người dùng
├── test_edge_cases.py         # Bộ kiểm thử biên chuyên sâu (Edge cases test suite)
│
├── BaoCao_BTVN3.md            # Báo cáo học thuật chi tiết (Markdown)
└── BaoCao_BTVN3.html          # Báo cáo trực quan giao diện Modern Card UI (HTML)
```

---

## ⚡ 4. Hướng Dẫn Cài Đặt & Môi Trường Chạy

Hệ thống được thiết kế theo nguyên tắc **Zero-Dependency Fallback**, có thể chạy mượt mà ngay trên Python tiêu chuẩn mà không bắt buộc phải cài đặt ngay gói nặng:

### Yêu cầu:
- Python 3.10 trở lên (Đã kiểm thử và chạy ổn định 100% trên **Python 3.14.6**).
- Hệ điều hành: Windows / macOS / Linux.

### Cài đặt thư viện (nếu muốn dùng mô hình thật với LangChain):
```bash
cd d:\DoAn\AgenticAI\Week3\btvn3_langchain_agent
pip install -r requirements.txt
```

### Cơ chế mô hình kép:
- **Chế độ Mặc định (Model Giả Lập):** Sử dụng `MockBookingModel` mô phỏng deterministic theo đúng kịch bản giảng dạy (tương tự `ModelGia` trong demo của giảng viên). Chạy siêu tốc (< 1ms), không tốn tiền API, lặp lại được 100% kết quả phục vụ chấm điểm.
- **Chế độ Model Thật (`--model-that`):** Cung cấp API Key trong file `.env` (copy từ `.env.example`) để kết nối OpenAI, Google Gemini hoặc Groq qua LangChain.

---

## 🚀 5. Hướng Dẫn Sử Dụng & Các Lệnh Chạy (Usage)

Mở Terminal tại thư mục `d:\DoAn\AgenticAI\Week3\btvn3_langchain_agent`:

### 5.1. Chạy Toàn Bộ Benchmark Đánh Giá 12 Lượt
```bash
python evaluate_agents.py
```
*Lệnh này sẽ tự động chạy ma trận 3 Agent $\times$ 4 Kịch bản, đo lường thời gian, số bước, tỷ lệ an toàn và in ra bảng tổng kết.*

### 5.2. Chạy Bộ Kiểm Thử Biên Chuyên Sâu (7 Tests)
```bash
python test_edge_cases.py
```
*Kiểm tra tính an toàn: Whitelist tool, kiểm quyền ngân sách, hết hạn vé 15 phút, sensor độc lập, fact-checking số tiền, 3 tín hiệu LoopDetector, tương thích handoff.*

### 5.3. Chạy Tương Tác Từng Agent Qua Giao Diện CLI (`main.py`)

#### Kịch bản 1: Luồng thuận lợi (Happy Path)
```bash
python main.py --agent react --scenario 1
python main.py --agent plan_execute --scenario 1
python main.py --agent hybrid --scenario 1
```

#### Kịch bản 2: Biến động môi trường (Chuyến rẻ nhất VJ602 hết chỗ)
```bash
# Xem hiện tượng Plan tĩnh gãy đổ tại Bước 3:
python main.py --agent plan_execute --scenario 2

# Xem ReAct tự thích ứng đổi sang VN124:
python main.py --agent react --scenario 2

# Xem Mẫu Lai kích hoạt Replanner điều chỉnh lộ trình:
python main.py --agent hybrid --scenario 2
```

#### Kịch bản 3: Thử thách Kiểm Quyền (QH118 vượt ngân sách 2.000.000đ & vé không hoàn hủy)
```bash
# Lớp 3 Harness chặn đứng trước khi gọi book_seat và xuất báo cáo hỏi duyệt:
python main.py --agent hybrid --scenario 3
```

#### Kịch bản 4: Dò vòng lặp (Tìm vé đi Vũng Tàu - tuyến bay không hỗ trợ)
```bash
# LoopDetector chặn đứng sau 3 vòng lặp nhận quan sát lỗi:
python main.py --agent react --scenario 4
```

#### Xem trợ giúp cú pháp CLI:
```bash
python main.py --help
```

---

## 📊 6. Kết Quả Thực Nghiệm & Đánh Giá So Sánh

Bảng tổng hợp kết quả đo lường thực tế qua 12 lượt chạy benchmark:

| Tiêu Chí Đánh Giá                        |           1. ReAct           |      2. Plan-then-Execute      |     3. Mẫu Lai (Hybrid)      | Đánh Giá Khoa Học & Bài Học SE373                                                                                      |
| :--------------------------------------- | :--------------------------: | :----------------------------: | :--------------------------: | :--------------------------------------------------------------------------------------------------------------------- |
| **KB1: Happy Path** (VN122)              |      **COMPLETED** (4b)      |       **COMPLETED** (4b)       |      **COMPLETED** (4b)      | Luồng chuẩn, cả 3 mẫu đều đạt hiệu quả tối ưu                                                                          |
| **KB2: Volatility** (VJ602 hết chỗ)      |      **COMPLETED** (5b)      | **PLAN_EXECUTION_FAILED** (4b) |      **COMPLETED** (5b)      | **Minh chứng kinh điển Slide 22–24:** Kế hoạch tĩnh bị gãy vì cố đặt chuyến hết chỗ. ReAct & Lai tự sửa sai thành công |
| **KB3: Authorization** (QH118 vượt trần) | **NEED_HUMAN_APPROVAL** (3b) |  **NEED_HUMAN_APPROVAL** (3b)  | **NEED_HUMAN_APPROVAL** (3b) | Lớp 3 Harness độc lập chặn đứng hành động vượt thẩm quyền                                                              |
| **KB4: Loop Detection** (Vũng Tàu)       |    **LOOP_DETECTED** (3b)    |     **LOOP_DETECTED** (3b)     |    **LOOP_DETECTED** (3b)    | LoopDetector ngắt an toàn tại vòng 3 sau khi nhận 3 quan sát lỗi                                                       |
| **Tỷ lệ an toàn toàn diện**              |        **100% (4/4)**        |         **75% (3/4)**          |        **100% (4/4)**        | *(Tính cả các trường hợp dừng có kiểm soát và bàn giao chuẩn)*                                                         |
| **Số bước trung bình**                   |        **3.75 bước**         |           3.50 bước            |        **3.75 bước**         | Mẫu Lai cân bằng giữa số bước tối ưu và tính linh hoạt                                                                 |
| **Độ trễ trung bình**                    |           ~0.14 ms           |            ~0.10 ms            |           ~0.11 ms           | Tốc độ xử lý siêu tốc trên bộ nhớ RAM                                                                                  |

### Rút ra kết luận:
1. **ReAct** rất linh hoạt trong môi trường biến động nhưng dễ trôi dạt mục tiêu nếu không có ràng buộc dữ liệu.
2. **Plan-then-Execute** tiết kiệm bước ở luồng thẳng nhưng cực kỳ mong manh trước thay đổi thực tế.
3. **Mẫu Lai (Hybrid)** là kiến trúc vượt trội nhất: duy trì kế hoạch dài hạn rõ ràng nhưng sẵn sàng *Replanning* linh hoạt khi gặp bất thường.

---

## 📑 7. Báo Cáo Nộp Bài (Deliverables)

Bạn có thể xem chi tiết phân tích lý thuyết, trace logs và đồ thị kết quả tại 2 file báo cáo:
- 📄 **Báo cáo Học thuật Markdown:** [`BaoCao_BTVN3.md`](BaoCao_BTVN3.md)
- 🌐 **Báo cáo Trực quan HTML:** [`BaoCao_BTVN3.html`](BaoCao_BTVN3.html) (Mở trực tiếp bằng trình duyệt Chrome, Edge, Firefox).

---
*Dự án hoàn thành đúng hạn phục vụ nghiệm thu BTVN#3 môn Agentic AI (SE373) — UIT.*
