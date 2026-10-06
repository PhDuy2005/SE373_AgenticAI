<p align="center">
  <a href="https://www.uit.edu.vn/" title="University of Information Technology" style="border: none;">
    <img src="https://i.imgur.com/WmMnSRt.png" alt="University of Information Technology (UIT)">
  </a>
</p>

<h1 align="center"><b>SE373 - Kỹ thuật xây dựng hệ thống Agentic AI</b></h1>
<h3 align="center"><i>(Agentic AI Engineering for Software Systems)</i></h3>

# Course Portfolio & Weekly Lab Reports

> Repository này lưu trữ toàn bộ bài tập lý thuyết, báo cáo thực hành và mã nguồn dự án cho môn học **SE373 – Kỹ thuật xây dựng hệ thống Agentic AI (Agentic AI Engineering for Software Systems)** tại Trường Đại học Công nghệ Thông tin (UIT – ĐHQG-HCM).  
> 
> Báo cáo được cập nhật và hệ thống hóa hàng tuần, bao gồm tài liệu lý thuyết, mã nguồn hoàn chỉnh, ảnh chụp minh chứng thực nghiệm và các bản báo cáo độc lập.

---

## Author Information
|  No. | Student ID | Full Name           | Role                | Github                                     | Email                  |
| ---: | :--------: | ------------------- | ------------------- | ------------------------------------------ | ---------------------- |
|    1 |  23520384  | Pham Tran Khanh Duy | Student / Developer | [PhDuy2005](https://github.com/PhDuy2005/) | 23520384@gm.uit.edu.vn |

---

## 🗺️ Weekly Roadmap & Report Navigation (Bản Đồ Kết Nối Báo Cáo)

Dưới đây là bảng điều hướng nhanh đến báo cáo và tài liệu thực hành của từng tuần trong học kỳ:

|    Tuần     | Chủ Đề / Dự Án                              | Nội Dung Trọng Tâm                                                                                                                                                                     | Thư Mục / Báo Cáo                                                                                                                                                                                                                                                                      |                   Trạng Thái                   |
| :---------: | :------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------: |
| **Week 01** | **Lý Thuyết Nền Tảng Agentic AI**           | • Tổng quan về Agentic AI & Agentic Workflows<br>• Phân biệt LLM truyền thống và Agent tự chủ<br>• Ứng dụng trong Kỹ thuật Phần mềm                                                    | 📁 [`LiThuyet-Week1/`](LiThuyet-Week1/)<br>📄 [Báo cáo PDF](LiThuyet-Week1/23520384-PhamTranKhanhDuy-Week1.pdf)<br>📝 [Báo cáo DOCX](LiThuyet-Week1/23520384-PhamTranKhanhDuy-Week1.docx)                                                                                                 | <span style="color:green">**Completed**</span> |
| **Week 02** | **Phân Loại Sự Cố (Software Issue Triage)** | • LLM Minimal Call & Đánh giá Token (`tiktoken`)<br>• Structured Output với Pydantic Validation<br>• Application-Controlled Function Calling<br>• Streamlit Web UI & Xuất Báo Cáo HTML | 📁 [`Week2/Demo-Issue-Triage/`](Week2/Demo-Issue-Triage/)<br>📖 [**Báo cáo Chi Tiết README**](Week2/Demo-Issue-Triage/README.md)<br>📘 [Hướng dẫn Demo Guide](Week2/Demo-Issue-Triage/demo-guide.html)<br>🌐 [Kết quả Web UI (HTML)](Week2/Demo-Issue-Triage/streamlit-triage-result.html) | <span style="color:green">**Completed**</span> |
| **Week 03** | **Agent Fundamentals & Agent Đặt Vé Máy Bay** | • Vòng lặp Agent, ReAct, Plan-then-Execute và Hybrid<br>• Harness 4 lớp, điều kiện dừng và xử lý lỗi<br>• Benchmark 3 agent trên 4 kịch bản | 📁 [`Week3/`](Week3/)<br>📖 [README Week 3](Week3/README.md)<br>📄 [Báo cáo BTVN#3 (Markdown)](Week3/btvn3_langchain_agent/BaoCao_BTVN3.md)<br>🌐 [Báo cáo BTVN#3 (HTML)](Week3/btvn3_langchain_agent/BaoCao_BTVN3.html) | <span style="color:green">**Completed**</span> |
| **Week 04** | *(Kế hoạch học tập)*                        | • Tiếp tục cập nhật theo tiến độ môn học...                                                                                                                                            | 📁 `Week4/`                                                                                                                                                                                                                                                                             |                   *Upcoming*                   |

---

## 📂 Cấu Trúc Repository

```text
./ (Repository Root)
├── README.md                           <-- (File này) Bản đồ kết nối báo cáo môn học
├── LiThuyet-Week1/                     <-- Báo cáo lý thuyết Tuần 01
│   ├── 23520384-PhamTranKhanhDuy-Week1.docx
│   └── 23520384-PhamTranKhanhDuy-Week1.pdf
├── Week2/                              <-- Thực hành & Dự án Tuần 02
│   └── Demo-Issue-Triage/              <-- Mã nguồn & Báo cáo hoàn chỉnh Tuần 02
│       ├── README.md                   <-- Báo cáo chi tiết kết quả thực hành Tuần 02
│       ├── demo-guide.html             <-- Tài liệu hướng dẫn thực hành gốc
│       ├── streamlit-triage-result.html <-- Kết quả Web UI dạng HTML độc lập
│       ├── 00_minimal_triage.py        <-- Demo 00: Prose output
│       ├── 01_measure_tokens.py        <-- Demo 01: Offline token measurement
│       ├── 02_structured_output.py     <-- Demo 02: Constrained structured output
│       ├── 03_function_calling.py      <-- Demo 03: Application-controlled tool calling
│       ├── 04_streamlit_triage.py      <-- Demo 04/05: Streamlit Web UI & HTML Export
│       ├── triage_workflow.py          <-- Shared triage logic & tool definition
│       ├── demo_common.py              <-- Shared client & env loaders
│       ├── demo-01-result.png          <-- Minh chứng Demo 00
│       ├── demo-02-result.png          <-- Minh chứng Demo 01
│       ├── demo-03-result.png          <-- Minh chứng Demo 02
│       ├── demo-04-result.png          <-- Minh chứng Demo 03
│       └── requirements.txt            <-- Dependencies của dự án
└── Week3/                              <-- Tài liệu học phần & BTVN#3: Agent Fundamentals
    ├── README.md                       <-- Bản đồ tài liệu và hướng dẫn nhanh Week 3
    ├── SE373_Agent_Fundamentals_Week3.md <-- Giáo trình Buổi 03
    ├── Week3-requirment.md             <-- Đề bài BTVN#3
    ├── KeHoach_BTVN3.md                <-- Kế hoạch triển khai kỹ thuật
    └── btvn3_langchain_agent/          <-- Agent đặt vé máy bay bằng LangChain/LangGraph
        ├── README.md                   <-- Hướng dẫn dự án, cài đặt và chạy
        ├── .env.example                <-- Mẫu cấu hình môi trường
        ├── requirements.txt            <-- Dependencies của dự án
        ├── mock_flight_tools.py        <-- Công cụ đặt vé mô phỏng
        ├── flight_harness.py           <-- Harness 4 lớp, LoopDetector và BudgetManager
        ├── model_provider.py           <-- Mock model và provider LLM
        ├── agent_react.py              <-- Agent theo mẫu ReAct
        ├── agent_plan_execute.py       <-- Agent theo mẫu Plan-then-Execute
        ├── agent_hybrid.py             <-- Agent theo mẫu Hybrid
        ├── evaluate_agents.py          <-- Benchmark 12 lượt trên 4 kịch bản
        ├── test_edge_cases.py          <-- Kiểm thử các trường hợp biên
        ├── main.py                     <-- CLI tương tác
        ├── BaoCao_BTVN3.md             <-- Báo cáo học thuật Markdown
        └── BaoCao_BTVN3.html           <-- Báo cáo trực quan HTML
```

---

## 🚀 Hướng Dẫn Nhanh Truy Cập Báo Cáo Từng Tuần

### 1. Báo cáo Tuần 01: Lý thuyết Agentic AI
* Mở trực tiếp file báo cáo PDF: [LiThuyet-Week1/23520384-PhamTranKhanhDuy-Week1.pdf](LiThuyet-Week1/23520384-PhamTranKhanhDuy-Week1.pdf)
* Hoặc file văn bản Word: [LiThuyet-Week1/23520384-PhamTranKhanhDuy-Week1.docx](LiThuyet-Week1/23520384-PhamTranKhanhDuy-Week1.docx)

### 2. Báo cáo Tuần 02: Software Issue Triage
* Xem toàn bộ báo cáo chi tiết, phân tích cải tiến và minh chứng: [**Week2/Demo-Issue-Triage/README.md**](Week2/Demo-Issue-Triage/README.md)
* Mở trang kết quả Web UI dạng tĩnh không cần chạy server: [Week2/Demo-Issue-Triage/streamlit-triage-result.html](Week2/Demo-Issue-Triage/streamlit-triage-result.html)
* Đọc tài liệu hướng dẫn kỹ thuật: [Week2/Demo-Issue-Triage/demo-guide.html](Week2/Demo-Issue-Triage/demo-guide.html)

---

## 🛠️ Yêu Cầu Môi Trường & Cài Đặt Chung

Để chạy các demo mã nguồn (Python):

1. **Yêu cầu Python:** Python 3.10 trở lên.
2. **Cài đặt thư viện phụ thuộc:**
   ```powershell
   # Di chuyển vào thư mục bài thực hành tương ứng (ví dụ Tuần 02):
   cd Week2/Demo-Issue-Triage

   # Tạo và kích hoạt môi trường ảo:
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Cài đặt packages:
   pip install -r requirements.txt
   ```
3. **Cấu hình API Key:**
   Sao chép `.env.example` thành `.env` và điền `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`.

