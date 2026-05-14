import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from gtts import gTTS
import io

# 1. 화면 설정 (다크모드에서도 무조건 연분홍 배경 + 진보라색 글씨)
st.set_page_config(page_title="고은이의 마법 단어장", layout="centered")

st.markdown("""
<style>
    /* 배경색: 연분홍 */
    .stApp { background-color: #FFF0F5 !important; }
    
    /* 모든 글자색을 '진보라색'으로 강제 고정 */
    h1, h2, h3, p, span, div, label, .stMarkdown, li, td {
        color: #4B0082 !important;
        font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif !important;
    }
    
    /* 탭 메뉴 글자 크기 및 색상 */
    .stTabs [data-baseweb="tab"] p {
        font-size: 18px;
        font-weight: bold;
    }

    /* 버튼 스타일 */
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        background-color: #9370DB !important;
        color: white !important;
        font-weight: bold !important;
        height: 3em;
    }
</style>
""", unsafe_allow_html=True)

st.title("🦄 고은이의 마법 단어장 PRO")

# 2. 구글 시트 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
    
    if df is None or df.empty:
        st.error("🚨 시트에 단어가 없어요! 구글 시트를 확인해주세요.")
        st.stop()
        
    # 데이터 전처리 (상태 칸 숫자 정리)
    df.columns = [c.strip() for c in df.columns]
    if '상태' not in df.columns: df['상태'] = 0
    df['상태'] = pd.to_numeric(df['상태'], errors='coerce').fillna(0).astype(int)
    
    # 아직 마스터 못한 단어들 (상태 4 미만)
    targets = df[df['상태'] < 4]

except Exception as e:
    st.error(f"🚨 연결 에러! 아빠, 공유 설정을 확인해주세요: {e}")
    st.stop()

# 3. 대망의 탭 4개 구성
tab1, tab2, tab3, tab4 = st.tabs(["👀 깜빡이", "📝 실전 퀴즈", "📊 단어 목록", "⚙️ 아빠 관리"])

# --- 탭 1: 깜빡이 (공부하기) ---
with tab1:
    st.subheader("먼저 눈으로 보며 외워봐요!")
    if len(targets) > 0:
        if 'f_idx' not in st.session_state: st.session_state.f_idx = 0
        word_row = targets.iloc[st.session_state.f_idx % len(targets)]
        
        st.markdown(f"""
        <div style="background:white; padding:50px; border-radius:30px; border:5px solid #FFB6C1; text-align:center; margin-bottom:20px;">
            <h1 style="font-size:80px; color:#4B0082;">{word_row['영어']}</h1>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔊 발음 듣기"):
                tts = gTTS(text=str(word_row['영어']), lang='en')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp, format='audio/mp3')
        with col2:
            if st.button("뜻 보기 / 다음 단어 ➡️"):
                st.info(f"💡 뜻: {word_row['한글']}")
                st.session_state.f_idx += 1
                time.sleep(1)
                st.rerun()
    else:
        st.success("고은아! 모든 단어를 다 공부했어! 👑")

# --- 탭 2: 퀴즈 (시험보기) ---
with tab2:
    if len(targets) == 0:
        st.success("마스터 완료! 아빠한테 단어 더 넣어달라고 하세요! ✨")
    else:
        if 'quiz_q' not in st.session_state:
            st.session_state.quiz_q = targets.sample(1).iloc[0]
        
        q = st.session_state.quiz_q
        st.markdown(f"<div style='text-align:center;'><h3>이 단어의 뜻은 무엇일까요?</h3><h1 style='font-size:60px;'>{q['영어']}</h1></div>", unsafe_allow_html=True)
        
        ans = st.text_input("정답을 입력하세요", key="q_input").strip()
        
        if st.button("정답 확인! 🚀"):
            if ans == str(q['한글']).strip():
                # 맞히면 상태 점수 1점 추가해서 시트에 저장
                idx = df[df['영어'] == q['영어']].index[0]
                df.at[idx, '상태'] = int(df.at[idx, '상태']) + 1
                conn.update(data=df)
                st.balloons()
                st.success("정답이야! 💖 점수가 올라갔어!")
                del st.session_state.quiz_q # 다음 문제를 위해 초기화
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("앗! 아쉬워요. 다시 한번 해볼까? 💪")

# --- 탭 3: 목록 (확인하기) ---
with tab3:
    st.subheader("📖 내가 공부하는 단어장")
    # 예쁘게 표로 보여주기
    st.table(df[['영어', '한글', '레벨']].head(20))

# --- 탭 4: 관리 (아빠용) ---
with tab4:
    st.subheader("⚙️ 관리자 설정")
    if st.text_input("비밀번호를 입력하세요", type="password") == "love317619":
        st.write("### 📊 현재 데이터 현황")
        st.dataframe(df)
