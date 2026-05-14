import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from gtts import gTTS
import io

# 1. 화면 설정 (연분홍 배경 + 진보라색 글씨)
st.set_page_config(page_title="고은이의 마법 단어장", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #FFF0F5 !important; }
    h1, h2, h3, p, span, div, label, .stMarkdown, li, td {
        color: #4B0082 !important;
        font-weight: bold !important;
    }
    .stButton>button {
        width: 100%; border-radius: 20px; background-color: #9370DB; color: white;
    }
</style>
""", unsafe_allow_html=True)

st.title("💖 고은이의 마법 단어장 Pro")

# 2. 구글 시트 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
    
    if df is None or df.empty:
        st.error("🚨 시트에 단어가 없어요! 구글 시트를 확인해주세요.")
        st.stop()
        
    # 데이터 전처리
    df.columns = [c.strip() for c in df.columns]
    if '상태' not in df.columns: df['상태'] = 0
    df['상태'] = pd.to_numeric(df['상태'], errors='coerce').fillna(0).astype(int)
    targets = df[df['상태'] < 4] # 아직 마스터 못한 단어들

except Exception as e:
    st.error(f"🚨 연결 에러! 아빠, 공유 설정을 확인해주세요: {e}")
    st.stop()

# 3. 탭 4개 구성 (이게 바로 아버님이 찾으시는 버전!)
tab1, tab2, tab3, tab4 = st.tabs(["👀 깜빡이", "📝 퀴즈", "📊 목록", "⚙️ 관리"])

# --- 탭 1: 깜빡이 (눈으로 익히기) ---
with tab1:
    st.subheader("눈으로 보며 먼저 외워봐요!")
    if len(targets) > 0:
        if 'f_idx' not in st.session_state: st.session_state.f_idx = 0
        row = targets.iloc[st.session_state.f_idx % len(targets)]
        
        st.markdown(f"""
        <div style="background:white; padding:50px; border-radius:30px; border:5px solid #FFB6C1; text-align:center;">
            <h1 style="font-size:70px;">{row['영어']}</h1>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("뜻 보기 / 다음 단어 ➡️"):
            st.info(f"뜻: {row['한글']}")
            st.session_state.f_idx += 1
            time.sleep(1)
            st.rerun()
    else:
        st.success("오늘 공부할 단어를 다 외웠어요! 👑")

# --- 탭 2: 퀴즈 (시험 보기) ---
with tab2:
    if len(targets) == 0:
        st.success("마스터 완료! 새 단어를 추가해주세요.")
    else:
        q = targets.sample(1).iloc[0]
        st.markdown(f"<div style='text-align:center;'><h3>뜻을 맞춰봐!</h3><h1>{q['영어']}</h1></div>", unsafe_allow_html=True)
        
        if st.button("🔊 발음 듣기"):
            tts = gTTS(text=str(q['영어']), lang='en')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            st.audio(fp, format='audio/mp3')

        ans = st.text_input("정답 입력", key="q_in").strip()
        if st.button("정답 확인! ✨"):
            if ans == str(q['한글']).strip():
                idx = df[df['영어'] == q['영어']].index[0]
                df.at[idx, '상태'] = int(df.at[idx, '상태']) + 1
                conn.update(data=df) # 시트에 바로 저장!
                st.balloons()
                st.success("천재! 정답이야! 💖")
                time.sleep(1)
                st.rerun()
            else:
                st.error("앗! 다시 한번 생각해보자! 💪")

# --- 탭 3: 목록 (전체 단어장 보기) ---
with tab3:
    st.subheader("📖 내 단어장 목록")
    st.table(df[['영어', '한글', '레벨']])

# --- 탭 4: 관리 (아빠 전용) ---
with tab4:
    if st.text_input("비밀번호", type="password") == "love317619":
        st.write("### 🛠️ 데이터 관리")
        st.dataframe(df)
        if st.button("새로고침 🔄"):
            st.rerun()
