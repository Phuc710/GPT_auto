import requests

def invite_member_to_team(email):
    # ============================================================
    # ⚠️ YÊU CẦU: https://platform.openai.com/settings/organization/admin-keys
    # ============================================================
    api_key = ""  # <-- Thay key này!
    
    # Endpoint chính thức (OpenAI Admin API)
    url = "https://api.openai.com/v1/organization/invites"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    data = {
        "email": email,
        "role": "reader"  # Các role: "owner", "reader"
    }
    
    try:
        print(f"🔄 Đang invite {email}...")
        response = requests.post(url, json=data, headers=headers)
        result = response.json()
        
        if response.status_code in [200, 201]:
            print(f"✅ Thành công! Đã gửi lời mời tới: {email}")
        else:
            print(f"❌ Lỗi {response.status_code}: {result}")
            
            # Gợi ý khắc phục
            error_msg = str(result)
            if "401" in str(response.status_code) or "invalid_api_key" in error_msg:
                print("💡 API key không hợp lệ hoặc không đủ quyền. Cần dùng sk-admin-... key!")
            elif "403" in str(response.status_code):
                print("💡 Key này không có quyền invite. Phải dùng Admin key!")
        
        return result
    except Exception as e:
        print(f"💥 Lỗi: {str(e)}")
        return str(e)

# Chạy
user_gmail = input("Nhập Gmail cần add vào team: ")
invite_member_to_team(user_gmail)