# SE373 · Buổi 03: Agent Fundamentals — BTVN#3

Thư mục này chứa toàn bộ tài liệu lý thuyết, demo trên lớp và giải pháp hoàn chỉnh cho **BTVN#3 (Dựng Agent Đặt Vé Máy Bay bằng LangChain & LangGraph)**.

---

## 📂 Cấu Trúc Thư Mục

1. **Thư mục giải pháp bài tập (Core Solution):**
   👉 **[`btvn3_langchain_agent/`](btvn3_langchain_agent/)**  
   Chứa toàn bộ mã nguồn, bộ harness 4 lớp, 3 mẫu thiết kế agent, bộ benchmark và 2 file báo cáo:
   - 📖 **[`btvn3_langchain_agent/README.md`](btvn3_langchain_agent/README.md)**: Hướng dẫn chi tiết dự án, cài đặt, lệnh chạy và phân tích kết quả.
   - 📄 **[`btvn3_langchain_agent/BaoCao_BTVN3.md`](btvn3_langchain_agent/BaoCao_BTVN3.md)**: Báo cáo học thuật chi tiết (Markdown).
   - 🌐 **[`btvn3_langchain_agent/BaoCao_BTVN3.html`](btvn3_langchain_agent/BaoCao_BTVN3.html)**: Báo cáo trực quan hiển thị trên trình duyệt (HTML).
   - 🧪 **[`btvn3_langchain_agent/evaluate_agents.py`](btvn3_langchain_agent/evaluate_agents.py)**: Runner benchmark ma trận 12 lượt.
   - 💻 **[`btvn3_langchain_agent/main.py`](btvn3_langchain_agent/main.py)**: Giao diện CLI tương tác.

2. **Kế hoạch triển khai kỹ thuật đã duyệt:**
   - 📋 [`KeHoach_BTVN3.md`](KeHoach_BTVN3.md): Bản kế hoạch tổng thể (Master Implementation Plan).

3. **Tài liệu học phần gốc:**
   - 📑 [`SE373_Agent_Fundamentals_Week3.md`](SE373_Agent_Fundamentals_Week3.md): Giáo trình Buổi 03 (Vòng lặp Agent, Mẫu suy luận, Điều kiện dừng, 4 Failure Modes).
   - 📝 [`Week3-requirment.md`](Week3-requirment.md): Đề bài yêu cầu của BTVN#3.
   - 🔬 [`Week-3/demo2-sv/`](Week-3/demo2-sv/): Mã nguồn demo của giảng viên trên lớp (`demo2_dieu_kien_dung.py`).

---

## ⚡ Chạy Nhanh Giải Pháp BTVN#3

```powershell
cd d:\DoAn\AgenticAI\Week3\btvn3_langchain_agent

# Chạy benchmark 12 lượt
python evaluate_agents.py

# Chạy bộ test biên chuyên sâu
python test_edge_cases.py

# Chạy CLI tương tác
python main.py --agent hybrid --scenario 2
```

Chi tiết xem tại: [`btvn3_langchain_agent/README.md`](btvn3_langchain_agent/README.md).
