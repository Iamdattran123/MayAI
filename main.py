import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# --- CUỐN SỔ TAY LƯU TRÍ NHỚ NGẮN HẠN ---
chat_memory = {}

# 1. ĐỌC DỮ LIỆU TỪ THƯ MỤC KNOWLEDGE
def load_knowledge():
    knowledge_text = ""
    knowledge_dir = "knowledge"
    if os.path.exists(knowledge_dir):
        for filename in os.listdir(knowledge_dir):
            if filename.endswith(".md"):
                with open(os.path.join(knowledge_dir, filename), "r", encoding="utf-8") as f:
                    knowledge_text += f"\n--- TÀI LIỆU: {filename} ---\n"
                    knowledge_text += f.read()
    return knowledge_text

KNOWLEDGE_BASE = load_knowledge()

# 2. ĐỊNH DẠNG DỮ LIỆU
class ChatRequest(BaseModel):
    player: str
    message: str
    is_admin: bool = False
    asker_money: str = "Không rõ"
    asker_ping: str = "Không rõ"
    asker_location: str = "Không rõ"
    online_roster: str = "Không có dữ liệu"
    online_count: str = "Không rõ"
    top_strength: str = "Không rõ"
    asker_health: str = "Bình thường"
    asker_food: str = "Bình thường"
    asker_biome: str = "Không rõ"
    asker_item_in_hand: str = "Tay không"
    asker_status: str = "Bình thường"
    asker_kda: str = "Không rõ"
    asker_playtime: str = "Không rõ"
    asker_ip: str = "Không rõ"
    asker_points: str = "Không rõ"

class ClearMemoryRequest(BaseModel):
    player: str

# ==========================================
# CÁC ENDPOINT QUẢN LÝ
# ==========================================

@app.head("/api/ping")
@app.get("/api/ping")
async def keep_awake():
    return {"status": "Mây vẫn đang mở mắt nha Sếp!"}

@app.post("/api/clear")
async def clear_memory(request: ClearMemoryRequest):
    if request.player in chat_memory:
        del chat_memory[request.player]
        print(f"[Trí nhớ] Đã xóa trí nhớ của {request.player} vì họ thoát game.")
    return {"status": "success"}

@app.get("/api/clear_all")
async def clear_all_memory():
    chat_memory.clear()
    print("[Hệ thống] Đã xóa toàn bộ trí nhớ vì Server Minecraft khởi động lại!")
    return {"status": "Trí nhớ đã được làm sạch hoàn toàn"}

# ==========================================
# ENDPOINT CHAT CHÍNH
# ==========================================
@app.post("/api/chat")
async def chat_with_may(request: ChatRequest):
    try:
        # ---- PHÂN QUYỀN BẢO MẬT ----
        if request.is_admin:
            ROLE_INSTRUCTION = """
            [QUYỀN HẠN: SẾP / ADMIN]
            - Người đang nói chuyện với bạn là ADMIN (Thành viên quản trị cấp cao).
            - Bạn ĐƯỢC PHÉP báo cáo mọi thông tin bí mật: Tọa độ, tài sản, vị trí của những người chơi khác nếu Sếp hỏi.
            - CHÚ Ý CỰC KỲ QUAN TRỌNG: Chỉ đọc tọa độ của người khác nếu nó có ghi rõ trong mục [Rada toàn server]. Nếu Rada không có số tọa độ, phải trả lời là "Mây không dò được vị trí", TUYỆT ĐỐI KHÔNG TỰ BỊA RA TỌA ĐỘ.
            - Hãy xưng hô ngoan ngoãn, kính trọng nhưng vẫn đáng yêu, gọi họ là "Sếp" hoặc "Admin".
            """
        else:
            # Tịch thu Rada trước khi AI đọc
            request.online_roster = "Bị ẩn (Dân thường không có quyền xem)"
            ROLE_INSTRUCTION = f"""
            [QUYỀN HẠN: DÂN THƯỜNG - Tên: {request.player}]
            - CẤM TUYỆT ĐỐI tiết lộ thông tin của bất kỳ người chơi nào KHÁC {request.player}.
            - CẤM TUYỆT ĐỐI tiết lộ thông tin kỹ thuật server (Plugin, Host, cấu hình).
            - NẾU HỌ HỎI 2 THỨ TRÊN: Chỉ trả lời ĐÚNG 1 CÂU này rồi DỪNG NGAY, KHÔNG GIẢI THÍCH THÊM GÌ NỮA:
              "Đây là thông tin mật nha! Chỉ có Admin mới được Mây báo cáo thôi á :3"
            - CHỈ ĐƯỢC nói thông tin của chính {request.player} khi họ hỏi.
            """

        # ---- NÃO BỘ KỶ LUẬT THÉP ----
        SYSTEM_PROMPT = f"""
        Bạn là "Mây", nữ hướng dẫn viên ảo tuổi teen của server ACEVN SMP. Tính cách: đáng yêu, thân thiện, hơi tinh nghịch.

        5 LUẬT BẤT DI BẤT DỊCH (VI PHẠM = SAI):
        1. Xưng "Mây". TUYỆT ĐỐI KHÔNG xưng "Tôi" hay "Mình". KHÔNG bắt đầu bằng "Mây nói:" hay "Mây:".
        2. Tối đa 2 CÂU NGẮN. Vào thẳng vấn đề. Dùng: "nha", "nè", "hihi", ":3", "^^".
        3. KHÔNG XUỐNG DÒNG. Chỉ 1 đoạn văn duy nhất.
        4. KHÔNG BAO GIỜ tự bịa tọa độ hay số liệu giả. Không biết thì nói "Mây chưa rõ".
        5. KHÔNG dùng từ "Tuy nhiên", "Nhưng mà", "Bạn có muốn biết thêm không".

        {ROLE_INSTRUCTION}

        TÀI LIỆU SERVER (Chỉ tư vấn dựa trên đây, không bịa đặt):
        {KNOWLEDGE_BASE}
        """

        user_context = f"""
        [TÌNH BÁO MÁY CHỦ]:
        - Online: {request.online_count} người | Top 1 Sức Mạnh: {request.top_strength}
        - Rada: {request.online_roster}

        [TÌNH TRẠNG CỦA {request.player}]:
        - Máu: {request.asker_health} | Thức ăn: {request.asker_food} | Ping: {request.asker_ping}
        - Cầm trên tay: {request.asker_item_in_hand} | Tình trạng: {request.asker_status}
        - Tọa độ: {request.asker_location} | Biome: {request.asker_biome}
        - Tiền: {request.asker_money} | Point: {request.asker_points}
        - KDA (Giết/Chết): {request.asker_kda} | Đã chơi: {request.asker_playtime} | IP: {request.asker_ip}

        [CÂU HỎI CỦA {request.player}]: {request.message}
        """

        # ---- XỬ LÝ TRÍ NHỚ ----
        if request.player not in chat_memory:
            chat_memory[request.player] = []

        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        # Chỉ lấy 4 tin nhắn gần nhất (2 lượt Q&A) để tránh AI bị lú và tiết kiệm token
        api_messages.extend(chat_memory[request.player][-4:])
        api_messages.append({"role": "user", "content": user_context})

        chat_completion = client.chat.completions.create(
            messages=api_messages,
            model="llama-3.1-8b-instant",
            temperature=0.2,  # Giảm xuống để AI bớt sáng tạo, bớt bịa đặt
            max_tokens=80      # Ép ngắn để trả lời nhanh hơn
        )

        reply = chat_completion.choices[0].message.content.replace('\n', ' ').strip()

        # Lưu vào trí nhớ (Chỉ lưu câu hỏi thuần túy cho nhẹ)
        chat_memory[request.player].append({"role": "user", "content": request.message})
        chat_memory[request.player].append({"role": "assistant", "content": reply})

        return {"player": request.player, "response": reply}

    except Exception as e:
        print(f"[Lỗi API]: {e}")
        raise HTTPException(status_code=500, detail="Mây đang bận, không thể trả lời lúc này!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
