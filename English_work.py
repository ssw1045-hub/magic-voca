import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from gtts import gTTS
import io

# 1. 화면 설정 (다크모드 방어 + 연분홍 인테리어)
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
        font-weight: bold; height: 3em;
    }
    input { color: black !important; }
</style>
""", unsafe_allow_html=True)

st.title("💖 고은이의 마법 단어장 PRO")

# 2. 구글 시트 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
    
    # 데이터 정리
    df.columns = [c.strip() for c in df.columns]
    if '상태' not in df.columns: df['상태'] = 0
    df['상태'] = pd.to_numeric(df['상태'], errors='coerce').fillna(0).astype(int)
    targets = df[df['상태'] < 4]

except Exception as e:
    st.error(f"🚨 연결 확인 중... (에러: {e})")
    st.stop()

# 3. 아버님이 찾으시던 4개 탭 구성
tab1, tab2, tab3, tab4 = st.tabs(["👀 깜빡이", "📝 퀴즈", "➕ 단어 추가", "⚙️ 관리"])

# --- 탭 1: 깜빡이 (암기 모드) ---
with tab1:
    st.subheader("먼저 눈으로 보며 외워봐요!")
    if len(targets) > 0:
        if 'f_idx' not in st.session_state: st.session_state.f_idx = 0
        row = targets.iloc[st.session_state.f_idx % len(targets)]
        st.markdown(f"<div style='background:white; padding:50px; border-radius:30px; border:5px solid #FFB6C1; text-align:center;'><h1>{row['영어']}</h1></div>", unsafe_allow_html=True)
        
        if st.button("🔊 발음 듣기", key="flash_audio"):
            tts = gTTS(text=str(row['영어']), lang='en')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            st.audio(fp, format='audio/mp3')
        
        if st.button("뜻 보기 / 다음 단어 ➡️"):
            st.info(f"💡 뜻: {row['한글']}")
            st.session_state.f_idx += 1
            time.sleep(1)
            st.rerun()
    else:
        st.success("모든 단어를 마스터했어요! 👑")

# --- 탭 2: 퀴즈 (시험 모드) ---
with tab2:
    if len(targets) == 0:
        st.success("공부할 단어가 없어요! '단어 추가' 탭에서 넣어주세요.")
    else:
        q = targets.sample(1).iloc[0]
        st.markdown(f"<div style='text-align:center;'><h3>이 단어의 뜻은?</h3><h1>{q['영어']}</h1></div>", unsafe_allow_html=True)
        ans = st.text_input("뜻을 입력하세요", key="quiz_in").strip()
        if st.button("정답 확인! ✨"):
            if ans == str(q['한글']).strip():
                idx = df[df['영어'] == q['영어']].index[0]
                df.at[idx, '상태'] += 1
                conn.update(data=df)
                st.balloons()
                st.success("정답이야! 💖")
                time.sleep(1)
                st.rerun()
            else:
                st.error("앗! 다시 한번 생각해보자! 💪")

# --- 탭 3: 단어 추가 (아빠가 직접 작성하는 곳!) ---
with tab3:
    st.header("📝 이번 시험 범위 단어 넣기")
    st.write("여기에 단어를 넣으면 즉시 퀴즈에 나타나고 구글 시트에도 저장돼요.")
    
    with st.form("add_form", clear_on_submit=True):
        new_eng = st.text_input("영어 단어 (예: apple)")
        new_kor = st.text_input("한글 뜻 (예: 사과)")
        new_lv = st.selectbox("레벨", ["중학", "고등", "기타"])
        submit = st.form_submit_button("단어장에 추가하기 🚀")
        
        if submit:
            if new_eng and new_kor:
                # 새 단어 데이터 생성
                new_data = pd.DataFrame([{
                    "영어": new_eng, "한글": new_kor, "레벨": new_lv, 
                    "상태": 0, "연속정답": 0, "배정일": "", "오답노트": "FALSE", "마스터일": ""
                }])
                # 기존 데이터와 합치기
                updated_df = pd.concat([df, new_data], ignore_index=True)
                conn.update(data=updated_df)
                st.success(f"'{new_eng}' 단어가 추가되었습니다! 퀴즈 탭으로 가보세요!")
            else:
                st.warning("영어와 한글 뜻을 모두 적어주세요.")

# --- 탭 4: 관리 (목록 및 삭제) ---
with tab4:
    if st.text_input("관리자 비번", type="password") == "love317619":
        st.write("### 📊 현재 전체 단어 목록")
        st.dataframe(df)
        if st.button("데이터 강제 새로고침 🔄"):
            st.rerun()
