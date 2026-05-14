import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from gtts import gTTS
import io

# 1. v8 버전의 화사한 인테리어 (연분홍 배경 + 진보라 글씨)
st.set_page_config(page_title="고은이의 마법 단어장", layout="centered")
st.markdown("""
<style>
    .stApp { background-color: #FFF0F5 !important; }
    h1, h2, h3, p, span, div, label, .stMarkdown, li, td {
        color: #4B0082 !important;
        font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif !important;
        font-weight: bold !important;
    }
    .stButton>button {
        width: 100%; border-radius: 20px; background-color: #9370DB !important; 
        color: white !important; font-weight: bold !important; height: 3.5em;
    }
    input { color: black !important; }
</style>
""", unsafe_allow_html=True)

st.title("💖 고은이의 마법 단어장 (v8 통합형)")

# 2. 구글 시트 연결 설정
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
    
    # 데이터 정리 및 '상태' 열 확보
    df.columns = [c.strip() for c in df.columns]
    if '상태' not in df.columns: df['상태'] = 0
    df['상태'] = pd.to_numeric(df['상태'], errors='coerce').fillna(0).astype(int)
    targets = df[df['상태'] < 4]

except Exception as e:
    st.error(f"🚨 연결 확인 중... (구글 시트 설정을 확인해주세요)")
    st.stop()

# 3. 아버님이 원하시는 4단 탭 구성
tab1, tab2, tab3, tab4 = st.tabs(["👀 깜빡이 학습", "📝 실전 퀴즈", "➕ 단어 직접 추가", "📊 단어장 목록"])

# --- 탭 1: 깜빡이 (v8 스타일) ---
with tab1:
    if len(targets) > 0:
        if 'f_idx' not in st.session_state: st.session_state.f_idx = 0
        row = targets.iloc[st.session_state.f_idx % len(targets)]
        st.markdown(f"<div style='background:white; padding:50px; border-radius:30px; border:5px solid #FFB6C1; text-align:center;'><h1>{row['영어']}</h1></div>", unsafe_allow_html=True)
        
        if st.button("🔊 발음 듣기", key="flash_audio"):
            tts = gTTS(text=str(row['영어']), lang='en')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            st.audio(fp, format='audio/mp3')
        
        if st.button("뜻 확인 / 다음 단어 ➡️"):
            st.info(f"💡 뜻: {row['한글']}")
            st.session_state.f_idx += 1
            time.sleep(1)
            st.rerun()
    else:
        st.success("고은아! 오늘 공부할 단어를 다 외웠어! 👑")

# --- 탭 2: 실전 퀴즈 (자동 업데이트) ---
with tab2:
    if len(targets) == 0:
        st.success("새로운 단어를 '단어 추가' 탭에서 넣어주세요!")
    else:
        # 무작위 문제 하나 선정
        if 'q_row' not in st.session_state: st.session_state.q_row = targets.sample(1).iloc[0]
        q = st.session_state.q_row
        
        st.markdown(f"<div style='text-align:center;'><h3>이 단어의 뜻은 무엇일까요?</h3><h1 style='font-size:50px;'>{q['영어']}</h1></div>", unsafe_allow_html=True)
        ans = st.text_input("정답 입력", key="quiz_in").strip()
        
        if st.button("정답 확인! ✨"):
            if ans == str(q['한글']).strip():
                # 맞히면 상태 점수 1점 추가해서 '구글 시트'에 저장
                idx = df[df['영어'] == q['영어']].index[0]
                df.at[idx, '상태'] += 1
                conn.update(data=df)
                st.balloons()
                st.success("천재! 정답이야! 구글 시트에도 기록됐어! 💖")
                del st.session_state.q_row
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("앗! 다시 한번 생각해보자! 💪")

# --- 탭 3: 단어 직접 추가 (아빠의 비밀 기능) ---
with tab3:
    st.header("📝 단어 직접 입력하기")
    st.write("여기서 단어를 넣으면 '구글 시트'와 '퀴즈'에 동시에 반영됩니다.")
    
    with st.form("add_word_form", clear_on_submit=True):
        new_eng = st.text_input("영어 단어")
        new_kor = st.text_input("한글 뜻")
        submitted = st.form_submit_button("단어장에 추가하기 🚀")
        
        if submitted:
            if new_eng and new_kor:
                new_row = pd.DataFrame([{"영어": new_eng, "한글": new_kor, "레벨": "중학", "상태": 0, "연속정답": 0, "배정일": "", "오답노트": "FALSE", "마스터일": ""}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.success(f"'{new_eng}' 단어가 구글 시트에 안전하게 추가되었습니다!")
            else:
                st.warning("단어와 뜻을 모두 입력해주세요.")

# --- 탭 4: 단어장 목록 (관리) ---
with tab4:
    st.subheader("📊 현재 고은이가 공부 중인 단어들")
    st.table(df[['영어', '한글', '상태']].head(20))
    if st.button("데이터 새로고침 (시트와 동기화) 🔄"):
        st.rerun()
