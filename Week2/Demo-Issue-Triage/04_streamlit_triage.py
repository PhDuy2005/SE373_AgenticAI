#!/usr/bin/env python3
"""Demo 04: Streamlit UI for Issue Triage with application-controlled function calling."""

from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime

import streamlit as st

from demo_common import load_environment, model_name, openai_client
from triage_workflow import TriageResult, triage_issue

DEFAULT_ISSUE = """Nút thanh toán trả HTTP 500 với mọi thẻ Visa từ 14:30.
Hãy triage issue và cho biết team nào cần xử lý."""

st.set_page_config(
    page_title="Issue Triage — Function Calling",
    page_icon="IT",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    """
    <style>
    [data-testid="stFormSubmitButton"] > button {
        background-color: #15803d;
        color: #ffffff;
    }
    [data-testid="stFormSubmitButton"] > button:hover {
        background-color: #166534;
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def generate_html_report(issue: str, result: TriageResult) -> str:
    """Generate a self-contained standalone HTML report of the issue triage results."""
    first_trace = result.tool_traces[0] if result.tool_traces else None
    component = first_trace.result.get("component", "Chưa rõ") if first_trace else "Chưa rõ"
    owner = first_trace.result.get("owner", "Chưa rõ") if first_trace else "Chưa rõ"

    traces_html_list = []
    for index, trace in enumerate(result.tool_traces, start=1):
        arg_json = json.dumps(trace.arguments, ensure_ascii=False, indent=2)
        res_json = json.dumps(trace.result, ensure_ascii=False, indent=2)
        traces_html_list.append(f"""
        <div class="trace-card">
            <div class="trace-title">
                <strong>{index}. Model yêu cầu tool</strong> <code>{html.escape(trace.name)}</code>
                <span class="badge">call_id: {html.escape(trace.call_id)}</span>
            </div>
            <div class="trace-section">
                <div class="trace-label">Arguments</div>
                <pre><code>{html.escape(arg_json)}</code></pre>
            </div>
            <div class="trace-section">
                <div class="trace-label">Application validate và thực thi</div>
                <pre><code>{html.escape(res_json)}</code></pre>
            </div>
        </div>
        """)
    traces_html = "\n".join(traces_html_list)

    escaped_response = html.escape(result.final_response)
    formatted_response = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped_response)
    formatted_response = re.sub(r"`(.+?)`", r"<code>\1</code>", formatted_response)
    formatted_response = formatted_response.replace("\n", "<br>")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Issue Triage Result</title>
    <style>
        :root {{
            --primary: #15803d;
            --primary-light: #f0fdf4;
            --primary-border: #bbf7d0;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --code-bg: #1e1e2e;
            --code-text: #cdd6f4;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem 1rem;
        }}
        .container {{
            max-width: 860px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #15803d 0%, #166534 100%);
            color: #ffffff;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        .header h1 {{ font-size: 1.8rem; margin-bottom: 0.5rem; }}
        .header p {{ opacity: 0.9; font-size: 0.95rem; }}
        .timestamp {{ font-size: 0.85rem; opacity: 0.75; margin-top: 0.5rem; }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }}
        .card h2 {{
            font-size: 1.25rem;
            margin-bottom: 1rem;
            color: var(--text);
            border-bottom: 2px solid var(--border);
            padding-bottom: 0.5rem;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .metric-card {{
            background: var(--primary-light);
            border: 1px solid var(--primary-border);
            border-radius: 8px;
            padding: 1.2rem;
        }}
        .metric-label {{
            font-size: 0.85rem;
            color: #166534;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .metric-value {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary);
            margin-top: 0.25rem;
        }}
        .issue-box {{
            background: #f1f5f9;
            border-left: 4px solid var(--primary);
            padding: 1rem;
            border-radius: 4px;
            font-style: normal;
            white-space: pre-wrap;
        }}
        .trace-card {{
            background: #f8fafc;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .trace-title {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}
        .badge {{
            background: #e2e8f0;
            color: #475569;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-family: monospace;
        }}
        .trace-section {{
            margin-top: 0.5rem;
        }}
        .trace-label {{
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 0.25rem;
        }}
        pre {{
            background: var(--code-bg);
            color: var(--code-text);
            padding: 0.85rem;
            border-radius: 6px;
            overflow-x: auto;
            font-family: "JetBrains Mono", Consolas, Monaco, monospace;
            font-size: 0.85rem;
        }}
        code {{
            font-family: "JetBrains Mono", Consolas, Monaco, monospace;
            background: #e2e8f0;
            color: #b91c1c;
            padding: 0.15rem 0.35rem;
            border-radius: 4px;
            font-size: 0.9em;
        }}
        pre code {{
            background: transparent;
            color: inherit;
            padding: 0;
        }}
        .final-response {{
            background: #ffffff;
            border-left: 4px solid var(--primary);
            padding: 1.25rem;
            border-radius: 4px;
            background: #fafafa;
            line-height: 1.7;
        }}
        @media (max-width: 600px) {{
            .metrics-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Kết Quả Issue Triage</h1>
            <p>Demo 04 — Streamlit UI with Application-Controlled Function Calling</p>
            <div class="timestamp">Thời gian: {now_str}</div>
        </div>

        <div class="card">
            <h2>Mô tả Issue</h2>
            <div class="issue-box">{html.escape(issue)}</div>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Component đã xác thực</div>
                <div class="metric-value">{html.escape(str(component))}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Team phụ trách</div>
                <div class="metric-value">{html.escape(str(owner))}</div>
            </div>
        </div>

        <div class="card">
            <h2>Trace Function Calling</h2>
            {traces_html}
        </div>

        <div class="card">
            <h2>Kết Quả Triage (Model Response)</h2>
            <div class="final-response">
                {formatted_response}
            </div>
        </div>
    </div>
</body>
</html>
"""


def render_result(result: TriageResult, issue: str = "") -> None:
    """Render the machine-visible tool trace before the model's final response."""
    first_trace = result.tool_traces[0]
    component_column, owner_column = st.columns(2)
    component_column.metric("Component đã xác thực", first_trace.result["component"])
    owner_column.metric("Team phụ trách", first_trace.result["owner"])

    with st.expander("Trace function calling", expanded=True):
        for index, trace in enumerate(result.tool_traces, start=1):
            st.markdown(f"**{index}. Model yêu cầu tool** `{trace.name}`")
            st.json({"id": trace.call_id, "arguments": trace.arguments})
            st.markdown("**Application validate và thực thi**")
            st.json(trace.result)

    st.subheader("Kết quả triage")
    st.markdown(result.final_response)

    st.divider()
    html_report = generate_html_report(issue, result)

    # Tự động lưu ra file streamlit-triage-result.html trong thư mục dự án
    output_filename = "streamlit-triage-result.html"
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(html_report)
        st.success(f"Đã tự động lưu kết quả vào `{output_filename}`")
    except Exception as err:
        st.warning(f"Không thể ghi file cục bộ: {err}")

    download_col, _ = st.columns([1, 1])
    with download_col:
        st.download_button(
            label="📥 Tải file HTML kết quả (Download HTML)",
            data=html_report,
            file_name=output_filename,
            mime="text/html",
            use_container_width=True,
        )

    with st.expander("📋 Xem và sao chép trực tiếp mã HTML"):
        st.caption("Bấm vào biểu tượng Copy ở góc trên bên phải khung code bên dưới:")
        st.code(html_report, language="html")


def main() -> None:
    load_environment()

    with st.sidebar:
        st.header("Runtime")
        st.write("OpenAI-compatible API")
        st.code(os.getenv("OPENAI_BASE_URL") or "Chưa cấu hình URL", language=None)
        st.write("Model")
        st.code(os.getenv("OPENAI_MODEL") or "Chưa cấu hình model", language=None)
        st.divider()
        st.write(
            "Application chỉ thực thi get_component_owner cho payment, identity và search."
        )

    st.title("Issue Triage")
    st.write("Demo 04 — model đề xuất tool call; application kiểm tra rồi mới thực thi.")

    with st.form("issue-triage-form"):
        issue = st.text_area(
            "Mô tả issue",
            value=DEFAULT_ISSUE,
            height=220,
            help="Nêu symptom, phạm vi ảnh hưởng và thời điểm bắt đầu nếu có.",
        )
        submitted = st.form_submit_button("Phân loại issue", type="primary", use_container_width=True)

    if not submitted:
        return
    if not issue.strip():
        st.error("Nhập mô tả issue trước khi chạy triage.")
        return

    try:
        with st.spinner("Đang gọi model và xử lý tool request…"):
            result = triage_issue(openai_client(), model_name(), issue.strip())
    except Exception as error:
        st.error(f"Triage không hoàn tất: {error}")
        st.info("Kiểm tra OPENAI_BASE_URL, OPENAI_MODEL và quyền truy cập model trong .env.")
        return

    st.success("Application đã hoàn tất function-calling flow.")
    render_result(result, issue.strip())


if __name__ == "__main__":
    main()
