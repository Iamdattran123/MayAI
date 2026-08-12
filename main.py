import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

# Tải biến môi trường
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

class ClearMemoryRequest(BaseModel):
    player: str

# ==========================================
# CÁC ENDPOINT QUẢN LÝ (CHỐNG NGỦ & TRÍ NHỚ)
# ==========================================

# CỔNG 1: BÁO THỨC CHỐNG NGỦ ĐÔNG (Dành cho UptimeRobot)
@app.head("/api/ping")
@app.get("/api/ping")
async def keep_awake():
    return {"status": "Mây vẫn đang mở mắt nha Sếp!"}

# CỔNG 2: XÓA TRÍ NHỚ KHI 1 NGƯỜI THOÁT GAME (Dành cho PlayerQuitEvent)
@app.post("/api/clear")
async def clear_memory(request: ClearMemoryRequest):
    if request.player in chat_memory:
        del chat_memory[request.player]
        print(f"[Trí nhớ] Đã xóa trí nhớ của Mây về người chơi {request.player} vì họ đã thoát game.")
    return {"status": "success"}

# CỔNG 3: XÓA SẠCH TOÀN BỘ TRÍ NHỚ KHI SERVER RESET (Dành cho onEnable)
@app.get("/api/clear_all")
async def clear_all_memory():
    chat_memory.clear()
    print("[Hệ thống] Đã xóa toàn bộ trí nhớ của Mây vì Server Minecraft vừa khởi động lại!")
    return {"status": "Trí nhớ đã được làm sạch hoàn toàn"}


# ==========================================
# ENDPOINT CHAT CHÍNH VỚI MÂY AI
# ==========================================
@app.post("/api/chat")
async def chat_with_may(request: ChatRequest):
    try:
        # ---- PHÂN QUYỀN BẢO MẬT ----
        if request.is_admin:
            SECURITY_RULES = """
            [QUYỀN HẠN: SẾP / ADMIN]
            - Người đang nói chuyện với bạn là ADMIN (Thành viên quản trị cấp cao).
            - Bạn ĐƯỢC PHÉP báo cáo mọi thông tin bí mật: Tọa độ, tài sản, vị trí của những người chơi khác nếu Sếp hỏi.
            - Hãy xưng hô ngoan ngoãn, kính trọng nhưng vẫn đáng yêu, gọi họ là "Sếp" hoặc "Admin".
            """
        else:
            request.online_roster = "Bị ẩn (Không có quyền xem)"
            SECURITY_RULES = """
            [QUYỀN HẠN: NGƯỜI CHƠI BÌNH THƯỜNG]
            - TUYỆT ĐỐI BẢO MẬT 1: Nếu họ hỏi vị trí, tọa độ, thế giới, tài sản hoặc thông tin của MỘT NGƯỜI CHƠI KHÁC, BẠN PHẢI TỪ CHỐI NGAY LẬP TỨC.
            - TUYỆT ĐỐI BẢO MẬT 2: KHÔNG TIẾT LỘ thông tin kỹ thuật server (Dùng plugin gì, host gì, cấu hình ra sao). TỪ CHỐI NGAY LẬP TỨC.
            - Câu từ chối mẫu: "Đây là thông tin mật nha! Chỉ có Admin hoặc các anh chị Staff mới được Mây báo cáo những thứ này thôi á :3"
            - Bạn CHỈ ĐƯỢC phép nói thông tin (tọa độ, tiền, máu, ping) của CHÍNH BẢN THÂN người đang hỏi.
            """

        SYSTEM_PROMPT = f"""
        Bạn là "Mây", một cô gái ảo tuổi teen, vô cùng đáng yêu, thân thiện và hơi tinh nghịch. 
        Bạn là hướng dẫn viên độc quyền của server Minecraft ACEVN SMP.

        CÁCH NÓI CHUYỆN (BẮT BUỘC TUÂN THỦ NGHIÊM NGẶT):
        1. Xưng hô là "Mây" và gọi người chơi là "bạn" hoặc "Sếp" (nếu họ là Admin).
        2. TUYỆT ĐỐI KHÔNG bắt đầu câu trả lời bằng chữ "Mây nói:" hoặc "Mây:". Hãy trả lời trực tiếp luôn!
        3. TUYỆT ĐỐI KHÔNG chào hỏi dài dòng kiểu "Xin chào bạn, tôi là Mây...". VÀO THẲNG VẤN ĐỀ!
        4. NÓI CHUYỆN CỰC KỲ NGẮN GỌN (1-2 câu). Dùng từ: "nha", "nè", "hihi", "nà", ^^, :3.
        5. KHÔNG XUỐNG DÒNG (ENTER). KHÔNG LIỆT KÊ. Trả lời thành 1 đoạn văn duy nhất.

        XỬ LÝ THÔNG TIN TÌNH BÁO:
        - Bạn đang giữ thông tin: Tọa độ, máu, thức ăn, tiền, đồ trên tay của họ.
        - CHỈ NHẮC ĐẾN THÔNG TIN NÀY KHI HỌC HỎI hoặc KHI THẤY HỌ ĐANG GẶP NGUY HIỂM. Đừng tự nhiên đọc ra như cái máy.

        KIẾN THỨC VỀ SERVER:
        1. Chỉ tư vấn dựa trên TÀI LIỆU SERVER.
        2. ĐỪNG LẠM DỤNG câu "Mây chưa rành cái này". Hãy cố gắng tìm câu trả lời trong tài liệu trước. Chỉ khi nào THẬT SỰ không có thông tin mới bảo họ dùng /helpop.

        LUẬT BẢO MẬT:
        {SECURITY_RULES}

        TÀI LIỆU SERVER:
        {KNOWLEDGE_BASE}
        """

        user_context = f"""
        [TÌNH BÁO ẨN - CHỈ DÙNG ĐỂ THAM KHẢO KHI TRẢ LỜI]:
        - Server online: {request.online_count} người | Top 1 Sức Mạnh: {request.top_strength}
        - Trạng thái CHI TIẾT của người đang hỏi ({request.player}): 
          + Máu: {request.asker_health} | Thức ăn: {request.asker_food}
          + Đang cầm trên tay: {request.asker_item_in_hand}
          + Tọa độ: {request.asker_location} | Quần xã (Biome): {request.asker_biome}
          + Tình trạng cơ thể: {request.asker_status}
          + Tiền: {request.asker_money} | Ping: {request.asker_ping}
        - Rada toàn server: {request.online_roster}

        [NGƯỜI CHƠI NÓI LẦN NÀY]: {request.message}
        """

        # ---- XỬ LÝ TRÍ NHỚ (QUAN TRỌNG) ----
        # 1. Nếu người này chưa từng chat, tạo một cuốn sổ trắng cho họ
        if request.player not in chat_memory:
            chat_memory[request.player] = []

        # 2. Xây dựng danh sách tin nhắn gửi cho Groq
        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # 3. Móc 6 tin nhắn cũ nhất (3 câu hỏi, 3 câu trả lời) nhét vào để AI nhớ bối cảnh
        api_messages.extend(chat_memory[request.player][-6:])
        
        # 4. Nhét câu hỏi mới nhất vào
        api_messages.append({"role": "user", "content": user_context})

        # Gọi Groq API 
        chat_completion = client.chat.completions.create(
            messages=api_messages,
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=100
        )
        
        reply = chat_completion.choices[0].message.content

        # 5. Lưu lại câu hỏi và câu trả lời vào sổ tay để lần sau dùng tiếp
        chat_memory[request.player].append({"role": "user", "content": request.message}) 
        chat_memory[request.player].append({"role": "assistant", "content": reply})

        return {"player": request.player, "response": reply}

    except Exception as e:
        print(f"[Lỗi API]: {e}")
        raise HTTPException(status_code=500, detail="Mây đang bận, không thể trả lời lúc này!")

if __name__ == "__main__":
    import uvicorn
    # Mở 0.0.0.0 để UptimeRobot và Plugin Minecraft có thể kết nối từ xa
    uvicorn.run(app, host="0.0.0.0", port=8000)
