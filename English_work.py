import streamlit as st
import pandas as pd
import time
from gtts import gTTS
import io

# 1. 고은이를 위한 마법 인테리어 (연분홍 배경 + 진보라 글씨)
st.set_page_config(page_title="고은이의 마법 단어장", layout="centered")
st.markdown("""
<style>
    .stApp { background-color: #FFF0F5 !important; }
    h1, h2, h3, p, span, div, label, .stMarkdown, td {
        color: #4B0082 !important;
        font-weight: bold !important;
    }
    .stButton>button {
        background-color: #9370DB !important; color: white !important;
        border-radius: 20px; height: 3em; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

st.title("🦄 고은이의 마법 단어장")

# 2. 구글 시트 직통 연결 (아버님이 성공하신 그 방식!)
SHEET_ID = "1sbHa2YDMuXtSH2GI37vikcf_oCKKoOXt34SLhL34gzY"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

try:
    df = pd.read_csv(URL)
    df.columns = [c.strip() for c in df.columns] # 공백 제거
    
    # 상태 칸 숫자 정리
    if '상태' not in df.columns: df['상태'] = 0
    df['상태'] = pd.to_numeric(df['상태'], errors='coerce').fillna(0).astype(int)
    
    targets = df[df['상태'] < 4]

    if len(targets) == 0:
        st.balloons()
        st.success("고은아! 모든 단어를 다 마스터했어! 최고야! 👑")
    else:
        # 단어 하나 뽑기
        q = targets.sample(1).iloc[0]
        
        # 퀴즈 카드
        st.markdown(f"""
        <div style="background:white; padding:50px; border-radius:30px; border:5px solid #FFB6C1; text-align:center; margin:20px 0;">
            <h1 style="font-size:80px; color:#4B0082;">{q['영어']}</h1>
        </div>
        """, unsafe_allow_html=True)

        # 🔊 발음 듣기 기능 추가!
        if st.button("🔊 원어민 발음 듣기"):
            tts = gTTS(text=str(q['영어']), lang='en')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            st.audio(fp, format='audio/mp3')

        ans = st.text_input("뜻을 입력하고 [정답 확인]을 누르세요", key="quiz_input").strip()
        
        if st.button("정답 확인! ✨"):
            if ans == str(q['한글']).strip():
                st.balloons()
                st.success("천재인데? 정답이야! 💖")
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("아쉬워! 다시 한번 생각해보자! 💪")

    # 관리용 표 (비밀번호 입력 시 노출)
    with st.expander("🔒 아빠 관리용"):
        if st.text_input("비밀번호", type="password") == "love317619":
            st.dataframe(df)

except Exception as e:
    st.error("시트를 불러오는 중이에요. 3초만 기다려주세요!")
