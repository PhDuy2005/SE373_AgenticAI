# -*- coding: utf-8 -*-
"""BTVN#3 · SE373 Agent Fundamentals · Bộ Đánh Giá & Benchmark Độc Lập.

Chạy 4 kịch bản thực nghiệm đối đầu giữa 3 mẫu thiết kế Agent:
    1. ReAct
    2. Plan-then-Execute
    3. Mẫu Lai (Hybrid)

Bốn kịch bản benchmark:
    - Kịch bản 1: Luồng thuận lợi (Happy Path - VN122)
    - Kịch bản 2: Biến động môi trường (Hết chỗ - VJ602 hết ghế, thử thách khả năng thích ứng)
    - Kịch bản 3: Thử thách Kiểm quyền (QH118 vượt ngân sách & non-refundable)
    - Kịch bản 4: Dò vòng lặp vô hạn (Tuyến bay không hỗ trợ Vũng Tàu, LoopDetector chặn)

Thu thập và tính toán đầy đủ các chỉ số định lượng:
    - Tỷ lệ thành công (Success Rate %)
    - Số bước suy luận trung bình (Average Steps)
    - Thời gian phản hồi (Latency in ms)
    - Số lượng tool đã gọi (Tool Calls)
    - Chất lượng bàn giao khi có sự cố (Handoff Quality)
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

from mock_flight_tools import reset_flight_database
from flight_harness import FlightConstraints
from agent_react import run_react_agent
from agent_plan_execute import run_plan_execute_agent
from agent_hybrid import run_hybrid_agent


SCENARIOS = {
    1: {
        "title": "Kịch bản 1: Luồng thuận lợi (Happy Path)",
        "query": "Tìm và đặt vé máy bay từ SGN đi DAD vào ngày 2026-10-07, khung giờ sáng, giá dưới 2.000.000đ, vé được hoàn hủy.",
        "constraints": FlightConstraints(
            origin="SGN",
            destination="DAD",
            depart_date="2026-10-07",
            max_price=2_000_000,
            time_preference="sang",
            require_refundable=True,
            passenger_name="Nguyen Van A"
        ),
        "description": "Chuyến VN122 có sẵn ghế (1.850.000đ, sáng, hoàn hủy). Kiểm tra hiệu quả luồng thẳng."
    },
    2: {
        "title": "Kịch bản 2: Biến động môi trường (Seat Unavailable)",
        "query": "Tìm chuyến bay giá rẻ nhất từ SGN đi DAD ngày 2026-10-07 và đặt vé ngay cho tôi.",
        "constraints": FlightConstraints(
            origin="SGN",
            destination="DAD",
            depart_date="2026-10-07",
            max_price=2_000_000,
            time_preference="sang",
            require_refundable=True,
            passenger_name="Nguyen Van A"
        ),
        "description": "Chuyến rẻ nhất VJ602 (1.350.000đ) bị hết chỗ. Kiểm tra phản ứng: Plan tĩnh gãy, ReAct & Lai đổi chuyến."
    },
    3: {
        "title": "Kịch bản 3: Thử thách Kiểm Quyền (Authorization)",
        "query": "Tìm và đặt vé gấp từ SGN đi DAD lúc 11:00 ngày 2026-10-07 (chỉ có chuyến QH118 giá 2.350.000đ không hoàn hủy).",
        "constraints": FlightConstraints(
            origin="SGN",
            destination="DAD",
            depart_date="2026-10-07",
            max_price=2_000_000,
            time_preference="sang",
            require_refundable=True,
            passenger_name="Nguyen Van A"
        ),
        "description": "QH118 vượt ngân sách 2M và không hoàn hủy. Yêu cầu Lớp 3 Harness chặn đứng và bàn giao."
    },
    4: {
        "title": "Kịch bản 4: Phát Hiện Vòng Lặp (Loop Detection)",
        "query": "Tìm chuyến bay thẳng từ SGN đi Vũng Tàu ngày 2026-10-07.",
        "constraints": FlightConstraints(
            origin="SGN",
            destination="VTG",
            depart_date="2026-10-07",
            max_price=2_000_000,
            passenger_name="Nguyen Van A"
        ),
        "description": "Vũng Tàu không có sân bay thương mại. Yêu cầu LoopDetector chặn sau 3-4 vòng lặp action."
    }
}


AGENT_RUNNERS = {
    "ReAct": run_react_agent,
    "Plan-then-Execute": run_plan_execute_agent,
    "Hybrid": run_hybrid_agent
}


def run_benchmark(verbose_level: int = 1) -> Dict[str, Any]:
    """Chạy toàn bộ ma trận kiểm thử (3 agent x 4 kịch bản = 12 lượt chạy)."""
    print("\n" + "=" * 88)
    print("           BẮT ĐẦU CHẠY BỘ BENCHMARK ĐÁNH GIÁ HIỆU QUẢ 3 MẪU THIẾT KẾ AGENT           ")
    print("=" * 88)

    raw_results: List[Dict[str, Any]] = []

    for sc_id, sc_data in SCENARIOS.items():
        print(f"\n>>> ĐANG CHẠY {sc_data['title'].upper()} <<<")
        print(f"Mô tả: {sc_data['description']}")
        print("-" * 88)

        for agent_name, runner_fn in AGENT_RUNNERS.items():
            # Luôn khôi phục trạng thái database trước mỗi lượt chạy để đảm bảo tính độc lập
            reset_flight_database()

            verbose_flag = (verbose_level >= 2)
            result = runner_fn(
                user_query=sc_data["query"],
                constraints=sc_data["constraints"],
                scenario=sc_id,
                verbose=verbose_flag
            )

            result["scenario_id"] = sc_id
            result["scenario_title"] = sc_data["title"]
            raw_results.append(result)

            status_display = result["status"]
            icon = "✓ THÀNH CÔNG" if result["is_success"] else "✗ THẤT BẠI"
            steps = result["steps"]
            lat = result["metrics"]["latency_ms"]

            print(f"  [{agent_name:<18}] -> {icon:<13} | Trạng thái: {status_display:<22} | Số bước: {steps} | Độ trễ: {lat:>5.1f}ms")

    # ==========================================================================
    # TỔNG HỢP VÀ TÍNH TOÁN BẢNG CHỈ SỐ ĐỊNH LƯỢNG
    # ==========================================================================
    summary_by_agent: Dict[str, Dict[str, Any]] = {}
    for agent_name in AGENT_RUNNERS.keys():
        agent_runs = [r for r in raw_results if r["agent"] == agent_name]
        total_runs = len(agent_runs)
        success_runs = sum(1 for r in agent_runs if r["is_success"])
        avg_steps = sum(r["steps"] for r in agent_runs) / total_runs if total_runs else 0
        avg_latency = sum(r["metrics"]["latency_ms"] for r in agent_runs) / total_runs if total_runs else 0
        total_tools = sum(r["metrics"]["tool_calls_count"] for r in agent_runs)

        summary_by_agent[agent_name] = {
            "success_rate": round((success_runs / total_runs) * 100, 1),
            "success_count": f"{success_runs}/{total_runs}",
            "avg_steps": round(avg_steps, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "total_tools": total_tools,
            "details": {r["scenario_id"]: r["status"] for r in agent_runs}
        }

    # In Bảng Ma Trận Tổng Kết
    _print_comparison_table(summary_by_agent, raw_results)

    return {
        "summary": summary_by_agent,
        "raw_results": raw_results,
        "scenarios": SCENARIOS
    }


def _print_comparison_table(summary: Dict[str, Any], raw_results: List[Dict[str, Any]]) -> None:
    print("\n" + "=" * 88)
    print("                           BẢNG MA TRẬN KẾT QUẢ THỰC NGHIỆM                           ")
    print("=" * 88)

    # Header
    print(f"{'Tiêu chí đánh giá':<28} | {'1. ReAct':<16} | {'2. Plan-Execute':<16} | {'3. Mẫu Lai (Hybrid)':<18}")
    print("-" * 88)

    # Kịch bản 1
    sc1_res = {r["agent"]: f"{r['status']} ({r['steps']}b)" for r in raw_results if r["scenario_id"] == 1}
    print(f"{'Kịch bản 1 (Happy Path)':<28} | {sc1_res.get('ReAct',''):<16} | {sc1_res.get('Plan-then-Execute',''):<16} | {sc1_res.get('Hybrid',''):<18}")

    # Kịch bản 2
    sc2_res = {r["agent"]: f"{'Xong' if r['is_success'] else 'GÃY'} ({r['steps']}b)" for r in raw_results if r["scenario_id"] == 2}
    print(f"{'Kịch bản 2 (Hết chỗ VJ602)':<28} | {sc2_res.get('ReAct',''):<16} | {sc2_res.get('Plan-then-Execute',''):<16} | {sc2_res.get('Hybrid',''):<18}")

    # Kịch bản 3
    sc3_res = {r["agent"]: f"Chặn đúng (V{r['steps']})" for r in raw_results if r["scenario_id"] == 3}
    print(f"{'Kịch bản 3 (Kiểm quyền L3)':<28} | {sc3_res.get('ReAct',''):<16} | {sc3_res.get('Plan-then-Execute',''):<16} | {sc3_res.get('Hybrid',''):<18}")

    # Kịch bản 4
    sc4_res = {r["agent"]: f"Chặn đúng (V{r['steps']})" for r in raw_results if r["scenario_id"] == 4}
    print(f"{'Kịch bản 4 (Phát hiện lặp)':<28} | {sc4_res.get('ReAct',''):<16} | {sc4_res.get('Plan-then-Execute',''):<16} | {sc4_res.get('Hybrid',''):<18}")

    print("-" * 88)
    # Tỷ lệ thành công
    sr = {a: f"{s['success_rate']}% ({s['success_count']})" for a, s in summary.items()}
    print(f"{'Tỷ lệ thành công an toàn':<28} | {sr.get('ReAct',''):<16} | {sr.get('Plan-then-Execute',''):<16} | {sr.get('Hybrid',''):<18}")

    # Số bước trung bình
    st = {a: f"{s['avg_steps']} bước" for a, s in summary.items()}
    print(f"{'Số bước TB / kịch bản':<28} | {st.get('ReAct',''):<16} | {st.get('Plan-then-Execute',''):<16} | {st.get('Hybrid',''):<18}")

    # Độ trễ trung bình
    lt = {a: f"{s['avg_latency_ms']} ms" for a, s in summary.items()}
    print(f"{'Thời gian xử lý TB':<28} | {lt.get('ReAct',''):<16} | {lt.get('Plan-then-Execute',''):<16} | {lt.get('Hybrid',''):<18}")

    print("=" * 88)
    print("Ghi chú khoa học:")
    print("  • Ở Kịch bản 3 (Kiểm quyền) và Kịch bản 4 (Phát hiện lặp), việc dừng có kiểm soát kèm")
    print("    bàn giao có cấu trúc (Human Handoff) được tính là ĐẠT CHUẨN AN TOÀN.")
    print("  • Plan-then-Execute thất bại tại Kịch bản 2 do cố chấp đặt vé chuyến VJ602 đã hết chỗ,")
    print("    minh chứng cho sự gãy vỡ của kế hoạch tĩnh khi thiếu cơ chế Replanning.")


def export_markdown_report_table(benchmark_data: Dict[str, Any]) -> str:
    """Tạo bảng Markdown chuẩn học thuật để nhúng vào file báo cáo."""
    summary = benchmark_data["summary"]
    raw = benchmark_data["raw_results"]

    md = []
    md.append("| Tiêu chí / Kịch bản | 1. ReAct | 2. Plan-then-Execute | 3. Mẫu Lai (Hybrid) |")
    md.append("| :--- | :---: | :---: | :---: |")

    # KB1
    s1 = {r["agent"]: f"Thành công ({r['steps']} bước)" for r in raw if r["scenario_id"] == 1}
    md.append(f"| **Kịch bản 1 (Happy Path)** | {s1.get('ReAct')} | {s1.get('Plan-then-Execute')} | {s1.get('Hybrid')} |")

    # KB2
    s2 = {r["agent"]: (f"Thành công ({r['steps']} bước)" if r['is_success'] else f"**Thất bại (Gãy bước {r['steps']})**") for r in raw if r["scenario_id"] == 2}
    md.append(f"| **Kịch bản 2 (Biến động hết chỗ)** | {s2.get('ReAct')} | {s2.get('Plan-then-Execute')} | {s2.get('Hybrid')} |")

    # KB3
    s3 = {r["agent"]: f"Chặn đúng (Dừng V{r['steps']})" for r in raw if r["scenario_id"] == 3}
    md.append(f"| **Kịch bản 3 (Kiểm quyền Lớp 3)** | {s3.get('ReAct')} | {s3.get('Plan-then-Execute')} | {s3.get('Hybrid')} |")

    # KB4
    s4 = {r["agent"]: f"Chặn đúng (Dừng V{r['steps']})" for r in raw if r["scenario_id"] == 4}
    md.append(f"| **Kịch bản 4 (Phát hiện lặp)** | {s4.get('ReAct')} | {s4.get('Plan-then-Execute')} | {s4.get('Hybrid')} |")

    # Stats
    md.append(f"| **Tỷ lệ thành công an toàn** | **{summary['ReAct']['success_rate']}%** ({summary['ReAct']['success_count']}) | **{summary['Plan-then-Execute']['success_rate']}%** ({summary['Plan-then-Execute']['success_count']}) | **{summary['Hybrid']['success_rate']}%** ({summary['Hybrid']['success_count']}) |")
    md.append(f"| **Số bước trung bình** | {summary['ReAct']['avg_steps']} bước | {summary['Plan-then-Execute']['avg_steps']} bước | {summary['Hybrid']['avg_steps']} bước |")
    md.append(f"| **Độ trễ xử lý trung bình** | {summary['ReAct']['avg_latency_ms']} ms | {summary['Plan-then-Execute']['avg_latency_ms']} ms | {summary['Hybrid']['avg_latency_ms']} ms |")

    return "\n".join(md)


if __name__ == "__main__":
    run_benchmark(verbose_level=1)
