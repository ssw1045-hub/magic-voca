import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import time
from datetime import datetime
from gtts import gTTS
import io

# 1. UI 및 다크모드 방어 설정
st.set_page_config(page_title="고은이의 마법 단어장", page_icon="🦄", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #FFF0F5 !important; }
    h1, h2, h3, p, span, div, label, .stMarkdown {
        color: #4B0082 !important;
        font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif !important;
    }
    .stButton>button {
        width: 100%; border-radius: 15px; border: 2px solid #9370DB;
        background-color: #FFFFFF !important; color: #4B0082 !important;
        font-weight: bold; padding: 12px; margin-bottom: 10px;
    }
    .quiz-box {
        background-color: #FFFFFF !important; padding: 30px;
        border-radius: 20px; border: 3px solid #FFB6C1;
        text-align: center; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(ttl="0s")

def update_data(df):
    conn.update(data=df)
    st.cache_data.clear()

# 데이터 로드 및 초기화
try:
    df = load_data()
    # 필요한 컬럼이 시트에 없을 경우 대비한 기본값 채우기
    for col in ['상태', '연속정답']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
except Exception as e:
    st.error("⚠️ 구글 시트 연결 중입니다... 잠시만 기다려주세요!")
    st.stop()

today_str = datetime.now().strftime("%Y-%m-%d")

# 3. 메인 화면
st.markdown("<h1 style='text-align: center;'>🦄 고은이의 마법 단어장</h1>", unsafe_allow_html=True)

# 통계 계산
targets = df[df['상태'] < 4]
mastered_today = len(df[df['마스터일'] == today_str])

st.markdown(f"### 🎀 오늘 미션 ({mastered_today} / 50개)")
st.progress(min(mastered_today / 50, 1.0))

st.write("---")

tab1, tab2, tab3 = st.tabs(["🎯 퀴즈 풀기", "👀 단어 보기", "🔒 아빠 관리"])

with tab1:
    if len(targets) == 0:
        st.balloons()
        st.success("오늘의 모든 단어를 마스터했어요! 대단해 고은아! 👑")
    else:
        # 무작위로 하나 추출
        q_row = targets.sample(1).iloc[0]
        st.markdown(f"<div class='quiz-box'><h1 style='font-size:60px;'>{q_row['영어']}</h1></div>", unsafe_allow_html=True)
        
        # 발음 듣기
        tts = gTTS(text=str(q_row['영어']), lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        st.audio(fp, format='audio/mp3')

        ans = st.text_input("한글 뜻은 무엇일까요?", key="quiz_input")
        if st.button("정답 확인! 🚀"):
            if ans.strip() == str(q_row['한글']).strip():
                idx = df[df['영어'] == q_row['영어']].index[0]
                df.at[idx, '상태'] += 1
                df.at[idx, '연속정답'] += 1
                if df.at[idx, '상태'] >= 4:
                    df.at[idx, '마스터일'] = today_str
                
                update_data(df)
                st.success("우와! 정답이야! ✨")
                time.sleep(1)
                st.rerun()
            else:
                st.error("앗! 다시 한번 생각해보자. 할 수 있어! 💪")

with tab2:
    st.subheader("👀 등록된 단어들을 확인해요")
    st.dataframe(df[['영어', '한글', '레벨', '상태']])

with tab3:
    if st.text_input("비밀번호", type="password") == "love317619":
        st.write("### 🛠️ 아빠 전용 관리 모드")
        st.write("구글 시트의 원본 데이터입니다.")
        st.dataframe(df)
        if st.button("데이터 강제 새로고침 🔄"):
            st.rerun()
