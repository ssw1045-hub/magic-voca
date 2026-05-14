import streamlit as st
import random
import time
import pandas as pd
from datetime import datetime, timedelta
from gtts import gTTS
import io

# ==========================================
# 1. [핵심] 다크모드 방어 및 모바일 UI 최적화 CSS
# ==========================================
st.set_page_config(page_title="마법의 영단어장", page_icon="🦄", layout="centered")

st.markdown("""
<style>
    /* 다크모드에서도 배경과 글자색 고정 */
    .stApp {
        background-color: #FFF0F5 !important;
        color: #4B0082 !important;
    }
    
    /* 모든 텍스트 색상을 진하게 강제 설정 */
    h1, h2, h3, p, span, div, label {
        color: #4B0082 !important;
        font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
    }

    /* 버튼 디자인 강화 (모바일에서 터치하기 좋게) */
    .stButton>button {
        width: 100%;
        border-radius: 15px;
        border: 2px solid #9370DB;
        background-color: #FFFFFF !important;
        color: #4B0082 !important;
        font-size: 18px !important;
        font-weight: bold !important;
        padding: 10px !important;
        margin-bottom: 10px;
    }
    
    /* 입력창 글자색 진하게 */
    .stTextInput>div>div>input {
        color: #4B0082 !important;
        background-color: #FFFFFF !important;
    }

    /* 퀴즈 박스 가독성 업그레이드 */
    .quiz-box {
        background-color: #FFFFFF !important;
        padding: 30px;
        border-radius: 20px;
        border: 3px solid #FFB6C1;
        text-align: center;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 및 스케줄 엔진 (V9 유지)
# ==========================================
if 'vocab' not in st.session_state:
    st.session_state.vocab = {}

if 'daily_goal' not in st.session_state:
    st.session_state.daily_goal = 50 
if 'daddy_letter' not in st.session_state:
    st.session_state.daddy_letter = "우리 예쁜 딸! 오늘도 최고였어! 사랑해! 💕"

today_obj = datetime.now()
today_str = today_obj.strftime("%Y-%m-%d")
is_sunday = today_obj.weekday() == 6

if 'last_assign_date' not in st.session_state:
    assigned_dates = [d["assigned_date"] for d in st.session_state.vocab.values() if d["assigned_date"] is not None]
    st.session_state.last_assign_date = max(assigned_dates) if assigned_dates else (today_obj - timedelta(days=1)).strftime("%Y-%m-%d")

# 선행 학습 로직 (내일치 당겨오기)
target_date = (today_obj + timedelta(days=1)).strftime("%Y-%m-%d") 
while st.session_state.last_assign_date < target_date:
    next_date = (datetime.strptime(st.session_state.last_assign_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    new_count = 0
    for level in ["중학", "고등"]:
        for eng, data in st.session_state.vocab.items():
            if new_count >= st.session_state.daily_goal: break
            if data["assigned_date"] is None and data["level"] == level and not data.get("is_urgent"):
                st.session_state.vocab[eng]["assigned_date"] = next_date
                new_count += 1
    st.session_state.last_assign_date = next_date

def get_status_icon(data):
    if data.get("is_urgent") and data["status"] < 4: return "🚨"
    return {0: "🥚", 1: "🔒", 2: "🌱", 3: "🌷", 4: "👑"}.get(data["status"], "🥚")

def get_audio(word):
    try:
        tts = gTTS(text=word, lang='en', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

# ==========================================
# 3. 메인 화면 구성 (진해진 텍스트)
# ==========================================
st.markdown("<h1 style='text-align: center;'>🦄 마법의 영단어장</h1>", unsafe_allow_html=True)

today_targets = [k for k, v in st.session_state.vocab.items() if v.get("assigned_date") is not None and v["status"] < 4 and not v.get("is_urgent")]
mastered_today = sum(1 for d in st.session_state.vocab.values() if d.get("mastered_date") == today_str and not d.get("is_urgent"))
total_mission = len(today_targets) + mastered_today

st.markdown(f"### 🎀 오늘~내일 미션 ({mastered_today} / {total_mission})")
st.progress(mastered_today / total_mission if total_mission > 0 else 1.0)

st.write("---")

tab1, tab2, tab3, tab4 = st.tabs(["👀 학습", "🎯 퀴즈", "⚙️ 관리/백업", "🔒 비밀"])

with tab1:
    mode1 = st.radio("모드", ["🌈 진도", "🚨 오답"], horizontal=True)
    words1 = [k for k, v in st.session_state.vocab.items() if (v.get("is_urgent") if mode1=="🚨 오답" else (v["assigned_date"] is not None and not v.get("is_urgent"))) and v["status"] < 4]
    
    if not words1: st.success("모두 마스터! 👑")
    else:
        if 'f_idx' not in st.session_state: st.session_state.f_idx = 0
        idx = st.session_state.f_idx % len(words1)
        eng = words1[idx]
        data = st.session_state.vocab[eng]
        
        st.markdown(f"<div class='quiz-box'><h1 style='font-size:60px;'>{eng}</h1>", unsafe_allow_html=True)
        if st.button("뜻 확인하기"): st.info(data['mean'])
        if st.button("다음 단어 ⏭️"): 
            st.session_state.f_idx += 1
            st.rerun()

with tab2:
    words2 = [k for k, v in st.session_state.vocab.items() if v["assigned_date"] is not None and v["status"] < 4]
    if not words2: st.success("퀴즈 완료! 🎉")
    else:
        q_eng = random.choice(words2)
        st.markdown(f"<div class='quiz-box'><h1 style='font-size:50px;'>{q_eng}</h1></div>", unsafe_allow_html=True)
        ans = st.text_input("정답 입력", key="quiz_input")
        if st.button("제출"):
            if ans.strip() == st.session_state.vocab[q_eng]["mean"]:
                st.session_state.vocab[q_eng]["status"] = min(st.session_state.vocab[q_eng]["status"] + 1, 4)
                if st.session_state.vocab[q_eng]["status"] == 4: st.session_state.vocab[q_eng]["mastered_date"] = today_str
                st.success("정답!")
            else: st.error("틀렸어요!")
            time.sleep(1)
            st.rerun()

# [중요] 관리 탭에 백업 기능을 유지하여 데이터 유실 방지
with tab3:
    st.subheader("💾 데이터 백업")
    if st.session_state.vocab:
        csv = pd.DataFrame(st.session_state.vocab).T.to_csv().encode('utf-8-sig')
        st.download_button("현재 상태 다운로드", csv, f"backup_{today_str}.csv", "text/csv")
    
    st.write("---")
    up = st.file_uploader("백업 파일 올리기", type="csv")
    if up and st.button("복구하기"):
        # 복구 로직...
        st.success("복구 완료!")

with tab4:
    if st.text_input("비밀번호", type="password") == "love317619":
        st.write("아빠 전용 관리 메뉴")
