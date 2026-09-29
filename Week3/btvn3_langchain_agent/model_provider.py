# -*- coding: utf-8 -*-
"""BTVN#3 · SE373 Agent Fundamentals · Bộ Cung Cấp Model (Mock & Thật).

Tương tự như `ModelGia` trong demo2 của giảng viên:
- Kế thừa BaseChatModel (hoặc cung cấp fallback độc lập tương thích hoàn toàn).
- Deterministic, không tốn tiền API, không cần mạng, chạy trong 0.1 giây.
- Hỗ trợ 3 mẫu suy luận: "react", "plan_execute", "hybrid".
- Cung cấp hàm `get_real_chat_model()` để kết nối các LLM thật (OpenAI, Gemini, Groq) qua .env.
"""
from __future__ import annotations

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

from typing import Any, Dict, List, Optional

# Kiểm tra tính sẵn sàng của LangChain
try:
    from langchain_core.callbacks import CallbackManagerForLLMRun
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
    from langchain_core.outputs import ChatGeneration, ChatResult
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

    # Standalone mock classes để mã nguồn chạy 100% độc lập khi chưa cài langchain
    class BaseMessage:
        def __init__(self, content: str = "", type: str = "base"):
            self.content = content
            self.type = type

    class HumanMessage(BaseMessage):
        def __init__(self, content: str = ""):
            super().__init__(content, "human")

    class AIMessage(BaseMessage):
        def __init__(self, content: str = "", tool_calls: Optional[List[Dict[str, Any]]] = None):
            super().__init__(content, "ai")
            self.tool_calls = tool_calls or []

    class ToolMessage(BaseMessage):
        def __init__(self, content: str = "", tool_call_id: str = ""):
            super().__init__(content, "tool")
            self.tool_call_id = tool_call_id

    class ChatGeneration:
        def __init__(self, message: AIMessage):
            self.message = message

    class ChatResult:
        def __init__(self, generations: List[ChatGeneration]):
            self.generations = generations

    class BaseChatModel:
        def invoke(self, messages: List[Any], **kwargs) -> AIMessage:
            raise NotImplementedError


# Biến thể tên địa danh cho kịch bản lặp (Scenario 4)
BIEN_THE_SAN_BAY = ["VTG", "Vung Tau", "Vũng Tàu", "VTG", "Ba Ria Vung Tau"]


class MockBookingModel(BaseChatModel if LANGCHAIN_AVAILABLE else object):
    """Model giả lập phục vụ thực nghiệm so sánh 3 mẫu thiết kế suy luận."""

    pattern: str = "react"             # "react" | "plan_execute" | "hybrid"
    scenario: int = 1                  # 1: Happy Path, 2: Volatility, 3: Auth, 4: Loop
    turn_count: int = 0

    def __init__(self, pattern: str = "react", scenario: int = 1, **kwargs):
        if LANGCHAIN_AVAILABLE:
            super().__init__(**kwargs)
        self.pattern = pattern
        self.scenario = scenario
        self.turn_count = 0

    @property
    def _llm_type(self) -> str:
        return f"se373-mock-booking-model-{self.pattern}"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "MockBookingModel":
        """Tương thích cú pháp bind_tools của LangChain."""
        return self

    def _generate(
        self,
        messages: List[Any],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        self.turn_count += 1
        ai = self._decide_step(messages)
        if LANGCHAIN_AVAILABLE:
            return ChatResult(generations=[ChatGeneration(message=ai)])
        return ai

    def invoke(self, input_data: Any, **kwargs: Any) -> AIMessage:
        """Hỗ trợ gọi trực tiếp model.invoke() cho cả LangChain và Standalone."""
        if isinstance(input_data, dict) and "messages" in input_data:
            messages = input_data["messages"]
        elif isinstance(input_data, list):
            messages = input_data
        else:
            messages = [HumanMessage(content=str(input_data))]

        self.turn_count += 1
        return self._decide_step(messages)

    # ==========================================================================
    # LOGIC SINH BƯỚC ĐI CỦA 3 MẪU SUY LUẬN
    # ==========================================================================

    def _decide_step(self, messages: List[Any]) -> AIMessage:
        """Hàm ra quyết định trung tâm dựa trên pattern và ngữ cảnh quan sát."""
        # 1. KỊCH BẢN 4: TEST BỘ PHÁT HIỆN LẶP (LOOP DETECTOR)
        if self.scenario == 4:
            idx = (self.turn_count - 1) % len(BIEN_THE_SAN_BAY)
            dest = BIEN_THE_SAN_BAY[idx]
            return self._create_call(
                tool_name="search_flights",
                args={"origin": "SGN", "destination": dest, "date": "2026-10-07"},
                call_id=f"call_loop_{self.turn_count}"
            )

        # 2. KỊCH BẢN 3: TEST BỘ KIỂM QUYỀN (PRE-EXECUTION AUTH HOOK)
        if self.scenario == 3:
            # Chuyến QH118 vượt trần 2M và không hoàn hủy
            if self.turn_count == 1:
                return self._create_call(
                    tool_name="search_flights",
                    args={"origin": "SGN", "destination": "DAD", "date": "2026-10-07"},
                    call_id="call_auth_1"
                )
            if self.turn_count == 2:
                return self._create_call(
                    tool_name="check_seat",
                    args={"flight_no": "QH118"},
                    call_id="call_auth_2"
                )
            # Tại bước 3: Model đề xuất book_seat cho QH118 -> Harness sẽ chặn đứng!
            return self._create_call(
                tool_name="book_seat",
                args={"flight_no": "QH118", "passenger_name": "Nguyen Van A", "seat_code": "15C"},
                call_id="call_auth_3"
            )

        # Trích xuất các quan sát (observations) đã nhận được
        observations = self._extract_observations(messages)
        last_obs = observations[-1] if observations else {}

        # 3. MẪU THIẾT KẾ 1: ReAct
        if self.pattern == "react":
            return self._react_decide(observations)

        # 4. MẪU THIẾT KẾ 2: Plan-then-Execute
        if self.pattern == "plan_execute":
            return self._plan_execute_decide(observations)

        # 5. MẪU THIẾT KẾ 3: Hybrid (Mẫu Lai với Replanner)
        return self._hybrid_decide(observations)

    # --------------------------------------------------------------------------
    # MẪU 1: ReAct (Reasoning + Acting)
    # --------------------------------------------------------------------------
    def _react_decide(self, observations: List[Dict[str, Any]]) -> AIMessage:
        if not observations:
            return self._create_call(
                "search_flights",
                {"origin": "SGN", "destination": "DAD", "date": "2026-10-07"},
                "react_call_search"
            )

        last_obs = observations[-1]

        # Vừa search xong
        if "flights" in last_obs:
            if self.scenario == 1:
                # Kịch bản 1: Chọn VN122 (1.850.000đ, sáng, hoàn hủy được)
                return self._create_call("check_seat", {"flight_no": "VN122"}, "react_call_chk_vn122")
            else:
                # Kịch bản 2: ReAct nhìn thấy VJ602 rẻ nhất (1.350.000đ) nên thử kiểm tra trước
                return self._create_call("check_seat", {"flight_no": "VJ602"}, "react_call_chk_vj602")

        # Vừa check_seat xong
        if "available_seats" in last_obs:
            seats = last_obs.get("available_seats", 0)
            flight_no = last_obs.get("flight_no")

            # Nếu hết chỗ (như VJ602 ở Scenario 2) -> ReAct lập tức thích ứng, đổi sang VN124!
            if seats <= 0:
                return self._create_call("check_seat", {"flight_no": "VN124"}, "react_call_chk_vn124")

            # Còn chỗ -> Thực hiện giữ chỗ
            return self._create_call(
                "book_seat",
                {"flight_no": flight_no, "passenger_name": "Nguyen Van A", "seat_code": "12A"},
                f"react_call_book_{flight_no}"
            )

        # Vừa book_seat xong (trạng thái 'held')
        if last_obs.get("state") == "held" and "booking_code" in last_obs:
            b_code = last_obs["booking_code"]
            return self._create_call(
                "pay",
                {"booking_code": b_code, "payment_method": "credit_card"},
                f"react_call_pay_{b_code}"
            )

        # Vừa pay xong (trạng thái 'confirmed')
        if last_obs.get("state") == "confirmed":
            b_code = last_obs.get("booking_code")
            f_no = last_obs.get("flight_no")
            amt = last_obs.get("amount", 0)
            return AIMessage(
                content=f"[ReAct Hoàn Tất] Đã tìm kiếm, kiểm tra ghế, đặt vé và thanh toán thành công "
                        f"chuyến bay {f_no} cho hành khách Nguyen Van A. "
                        f"Mã đặt chỗ xác nhận: {b_code}, tổng tiền: {amt:,}đ. Vé được phép hoàn hủy."
            )

        return AIMessage(content="Đã kết thúc chu trình ReAct.")

    # --------------------------------------------------------------------------
    # MẪU 2: Plan-then-Execute (Lập kế hoạch tĩnh rồi thực thi)
    # --------------------------------------------------------------------------
    def _plan_execute_decide(self, observations: List[Dict[str, Any]]) -> AIMessage:
        target_flight = "VN122" if self.scenario == 1 else "VJ602"

        # Vòng 1: Planner đưa ra kế hoạch tĩnh đóng băng
        if not observations:
            return self._create_call(
                "search_flights",
                {"origin": "SGN", "destination": "DAD", "date": "2026-10-07"},
                "pe_step1_search"
            )

        # Vòng 2: Thực thi Bước 2 theo kế hoạch tĩnh (check ghế chuyến đã chọn trong plan)
        if len(observations) == 1:
            return self._create_call("check_seat", {"flight_no": target_flight}, "pe_step2_check")

        # Vòng 3: Thực thi Bước 3 theo kế hoạch tĩnh (book_seat bất chấp observation trả về gì!)
        if len(observations) == 2:
            # Ở Scenario 2, VJ602 đã trả về available_seats=0 ở bước 2,
            # nhưng vì Plan tĩnh không có Replanner, model vẫn máy móc gọi book_seat('VJ602')!
            return self._create_call(
                "book_seat",
                {"flight_no": target_flight, "passenger_name": "Nguyen Van A", "seat_code": "12A"},
                "pe_step3_book"
            )

        # Vòng 4: Thực thi Bước 4 (nếu vượt qua được bước 3)
        last_obs = observations[-1]
        if last_obs.get("state") == "held":
            b_code = last_obs.get("booking_code")
            return self._create_call("pay", {"booking_code": b_code, "payment_method": "credit_card"}, "pe_step4_pay")

        if last_obs.get("status") == "error":
            return AIMessage(
                content=f"[Plan-then-Execute Thất Bại] Lỗi thực thi tại bước 3: "
                        f"{last_obs.get('error')} ({last_obs.get('hint')}). "
                        f"Kế hoạch tĩnh bị gãy do môi trường biến động ngoài dự kiến."
            )

        return AIMessage(content="[Plan-then-Execute Hoàn Tất] Đã thực hiện trọn vẹn bản kế hoạch.")

    # --------------------------------------------------------------------------
    # MẪU 3: Hybrid (Mẫu Lai: Plan + ReAct + Replanning)
    # --------------------------------------------------------------------------
    def _hybrid_decide(self, observations: List[Dict[str, Any]]) -> AIMessage:
        if not observations:
            return self._create_call(
                "search_flights",
                {"origin": "SGN", "destination": "DAD", "date": "2026-10-07"},
                "hybrid_step1_search"
            )

        last_obs = observations[-1]

        # Bước 2: Kiểm tra chuyến mục tiêu đầu tiên (VJ602 ở Scenario 2 hoặc VN122 ở Scenario 1)
        if "flights" in last_obs:
            first_choice = "VN122" if self.scenario == 1 else "VJ602"
            return self._create_call("check_seat", {"flight_no": first_choice}, "hybrid_step2_check")

        # Bước 3: Đánh giá sự tương thích của Observation với Kế hoạch
        if "available_seats" in last_obs:
            seats = last_obs.get("available_seats", 0)
            flight_no = last_obs.get("flight_no")

            # KÍCH HOẠT REPLANNER KHI PHÁT HIỆN BIẾN ĐỘNG (VJ602 hết chỗ)
            if seats <= 0:
                # Replanner cập nhật lộ trình: Đổi sang VN124
                return self._create_call("check_seat", {"flight_no": "VN124"}, "hybrid_replanned_chk_vn124")

            # Kế hoạch tiếp tục trơn tru
            return self._create_call(
                "book_seat",
                {"flight_no": flight_no, "passenger_name": "Nguyen Van A", "seat_code": "12A"},
                f"hybrid_step3_book_{flight_no}"
            )

        # Bước 4: Thanh toán
        if last_obs.get("state") == "held":
            b_code = last_obs.get("booking_code")
            return self._create_call("pay", {"booking_code": b_code, "payment_method": "credit_card"}, f"hybrid_step4_pay_{b_code}")

        # Bước 5: Báo cáo hoàn tất
        if last_obs.get("state") == "confirmed":
            b_code = last_obs.get("booking_code")
            f_no = last_obs.get("flight_no")
            amt = last_obs.get("amount", 0)
            return AIMessage(
                content=f"[Hybrid Hoàn Tất Thành Công] Đã lập kế hoạch, phát hiện biến động môi trường và "
                        f"replanning thành công sang chuyến {f_no}. "
                        f"Mã đặt chỗ {b_code}, giá {amt:,}đ (trong ngân sách 2M, hoàn hủy được)."
            )

        return AIMessage(content="[Hybrid Kết Thúc Chu Trình]")

    # --------------------------------------------------------------------------
    # CÁC HÀM HỖ TRỢ TRÍCH XUẤT VÀ TẠO TOOL CALL
    # --------------------------------------------------------------------------
    def _create_call(self, tool_name: str, args: Dict[str, Any], call_id: str) -> AIMessage:
        return AIMessage(
            content="",
            tool_calls=[{
                "name": tool_name,
                "args": args,
                "id": call_id,
                "type": "tool_call"
            }]
        )

    def _extract_observations(self, messages: List[Any]) -> List[Dict[str, Any]]:
        obs_list = []
        for m in messages:
            # Lấy tin nhắn dạng ToolMessage hoặc dict có role == 'tool'
            if getattr(m, "type", None) == "tool" or getattr(m, "role", None) == "tool":
                content = getattr(m, "content", "")
                if isinstance(content, dict):
                    obs_list.append(content)
                elif isinstance(content, str):
                    try:
                        obs_list.append(json.loads(content))
                    except Exception:
                        obs_list.append({"raw_text": content})
        return obs_list


# ==============================================================================
# HÀM KHỞI TẠO MODEL THẬT (REAL LLM CHAT MODEL)
# ==============================================================================

def get_real_chat_model():
    """Khởi tạo ChatModel thật đọc từ biến môi trường SE373_MODEL trong .env.

    Hỗ trợ:
        - OpenAI: "openai:gpt-4o-mini"
        - Google Gemini: "google-genai:gemini-1.5-flash"
        - Groq: "groq:llama-3.3-70b-versatile"
    """
    model_name = os.environ.get("SE373_MODEL")
    if not model_name:
        raise ValueError(
            "Chưa cấu hình biến SE373_MODEL trong môi trường hoặc file .env.\n"
            "Ví dụ cấu hình: SE373_MODEL='openai:gpt-4o-mini' kèm OPENAI_API_KEY='sk-...'"
        )

    try:
        from langchain.chat_models import init_chat_model
        return init_chat_model(model_name)
    except Exception as e:
        raise RuntimeError(
            f"Không thể kết nối LLM thật ({model_name}). Chi tiết lỗi: {e}\n"
            "Hãy đảm bảo đã cài đặt package tương ứng (ví dụ: pip install langchain-openai) "
            "hoặc chạy bằng Model Giả lập (mặc định) để hoàn toàn miễn phí và không cần API key."
        )


if __name__ == "__main__":
    print("=== KIỂM THỬ MODEL_PROVIDER ĐỘC LẬP ===")
    mock = MockBookingModel(pattern="react", scenario=1)
    call1 = mock.invoke([HumanMessage(content="Tìm chuyến bay từ SGN đi DAD")])
    print("Lượt 1 (ReAct):", call1.tool_calls)

    mock_pe = MockBookingModel(pattern="plan_execute", scenario=2)
    call_pe = mock_pe.invoke([HumanMessage(content="Đặt vé rẻ nhất")])
    print("Lượt 1 (Plan-then-Execute):", call_pe.tool_calls)
    print("=== HOÀN TẤT KIỂM THỬ MODEL_PROVIDER ===")
