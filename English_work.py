import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from gtts import gTTS
import io
from datetime import datetime

# ==========================================
# 1. UI/UX 디자인 (고급스러운 핑크 & 보라)
# ==========================================
st.set_page_config(page_title="고은이의 마법 단어장", layout="centered")
st.markdown("""
<style>
    .stApp { background-color: #FFF0F5 !important; }
    h1, h2, h3, p, span, div, label, li, td, th { color: #4B0082 !important; font-family: 'Apple SD Gothic Neo', sans-serif !important; font-weight: bold !important; }
    .stButton>button { width: 100%; border-radius: 15px; background: linear-gradient(135deg, #9370DB, #8A2BE2) !important; color: white !important; font-weight: bold; height: 3.5em; box-shadow: 0px 4px 6px rgba(0,0,0,0.2); }
    .flashcard { background: white; padding: 50px 20px; border-radius: 30px; border: 4px solid #FFB6C1; text-align: center; margin-bottom: 25px; box-shadow: 0px 10px 20px rgba(255,182,193,0.4); }
    .stCheckbox label { color: #4B0082 !important; font-size: 16px !important; }
</style>
""", unsafe_allow_html=True)

st.title("💖 고은이의 마법 단어장 V11")

# ==========================================
# 2. 데이터 로드 및 초기화
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
try:
    df = conn.read(ttl=0)
    # 필수 기둥: 영어, 한글, 상태, 학교오답, 시험용, 등록일
    required_cols = ['영어', '한글', '상태', '학교오답', '시험용', '등록일']
    for col in required_cols:
        if col not in df.columns: df[col] = ""
    df['상태'] = pd.to_numeric(df['상태'], errors='coerce').fillna(0).astype(int)
    today_str = datetime.today().strftime('%Y-%m-%d')
    df['등록일'] = df['등록일'].fillna(today_str).replace("", today_str)
except:
    st.error("🚨 시트 연결 실패! 설정을 확인해주세요.")
    st.stop()

# ==========================================
# 3. 누적 복습 알고리즘 (30개씩 누적)
# ==========================================
unmastered = df[df['상태'] < 4].reset_index(drop=True)
if not unmastered.empty:
    start_date = datetime.strptime(unmastered['등록일'].min(), '%Y-%m-%d')
    days_passed = (datetime.today() - start_date).days
    day_number = max(1, days_passed + 1)
    # 7일 누적 로직 (30개씩 추가)
    curr_limit = ((day_number - 1) % 7 + 1) * 30
    # 2주차 스와이프 (이전주 210개 포함)
    start_idx = max(0, ((day_number - 1) // 7 - 1) * 210)
    today_targets = unmastered.iloc[start_idx : start_idx + curr_limit + 180] # 2주 단위 포함
else:
    today_targets = pd.DataFrame()

# ==========================================
# 4. 4대 핵심 탭 구성
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["👀 깜빡이 학습", "🎯 마법 퀴즈", "➕ 단어 추가", "🔒 비밀의 방"])

# --- 탭 1: 깜빡이 학습 ---
with tab1:
    if not today_targets.empty:
        if 'f_idx' not in st.session_state: st.session_state.f_idx = 0
        row = today_targets.iloc[st.session_state.f_idx % len(today_targets)]
        
        # 강조 표시
        marks = []
        if str(row['학교오답']) == "O": marks.append("🚨학교오답")
        if str(row['시험용']) == "O": marks.append("📝시험단어")
        badge = " / ".join(marks) if marks else "✨ 일반학습"
        
        st.markdown(f"<div class='flashcard'><p style='color:#FF4500;'>{badge}</p><h1 style='font-size:70px;'>{row['영어']}</h1></div>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔊 발음"):
                tts = gTTS(text=str(row['영어']), lang='en')
                fp = io.BytesIO(); tts.write_to_fp(fp); st.audio(fp, format='audio/mp3')
        with c2:
            if st.button("💡 뜻 확인"): st.success(f"정답: {row['한글']}")
        if st.button("➡️ 다음 단어로 이동"):
            st.session_state.f_idx += 1
            st.rerun()
    else:
        st.success("오늘의 학습 분량을 모두 마쳤습니다! 👑")

# --- 탭 2: 마법 퀴즈 (무한 반복 & 기습 질문) ---
with tab2:
    st.write("### 🎯 실전 테스트")
    # [베테랑 아이디어] 무한 복습 모드 스위치
    review_mode = st.toggle("🔄 무한 복습 모드 (다 외운 단어도 포함해서 무작위 시험!)")
    
    quiz_pool = df if review_mode else today_targets
    
    if not quiz_pool.empty:
        if 'q_word' not in st.session_state:
            # 기습 질문: 오답이나 시험단어에 50% 가중치
            special = quiz_pool[(quiz_pool['학교오답']=="O") | (quiz_pool['시험용']=="O")]
            if not special.empty and datetime.now().second % 2 == 0: # 50% 확률로 기습 질문
                st.session_state.q_word = special.sample(1).iloc[0]
                st.session_state.is_surprise = True
            else:
                st.session_state.q_word = quiz_pool.sample(1).iloc[0]
                st.session_state.is_surprise = False
            st.session_state.q_done = False

        q = st.session_state.q_word
        header = "🔥 [기습 질문] 반드시 맞춰야 해!" if st.session_state.is_surprise else "이 단어의 뜻은?"
        st.markdown(f"<div class='flashcard'><h3>{header}</h3><h1 style='font-size:60px;'>{q['영어']}</h1></div>", unsafe_allow_html=True)
        
        if not st.session_state.q_done:
            ans = st.text_input("정답 입력", key=f"q_{q['영어']}").strip()
            if st.button("정답 확인 🚀"):
                st.session_state.q_done = True
                if ans == str(q['한글']).strip():
                    st.session_state.q_res = True
                    df_idx = df[df['영어'] == q['영어']].index[0]
                    df.at[df_idx, '상태'] += 1
                    conn.update(data=df)
                else:
                    st.session_state.q_res = False
                st.rerun()
        else:
            if st.session_state.q_res:
                st.balloons(); st.success(f"천재! 정답: {q['한글']}")
            else:
                st.error(f"앗! 정답은 '{q['한글']}'(이)야.")
            if st.button("➡️ 다음 문제"):
                del st.session_state.q_word
                st.rerun()
    else:
        st.write("문제가 없습니다.")

# --- 탭 3: 단어 추가 (유형 선택) ---
with tab3:
    st.header("📝 단어 추가")
    with st.form("add_v8", clear_on_submit=True):
        eng = st.text_input("영어 단어")
        kor = st.text_input("한글 뜻")
        col_a, col_b = st.columns(2)
        with col_a: is_wrong = st.checkbox("🏫 학교에서 틀린 단어")
        with col_b: is_test = st.checkbox("📝 이번 시험 범위 단어")
        
        if st.form_submit_button("마법의 시트에 저장 💾"):
            if eng and kor:
                new_row = pd.DataFrame([{"영어": eng, "한글": kor, "상태": 0, "학교오답": "O" if is_wrong else "X", "시험용": "O" if is_test else "X", "등록일": today_str}])
                conn.update(data=pd.concat([df, new_row], ignore_index=True))
                st.success("성공적으로 저장되었습니다!")
                time.sleep(1); st.rerun()

# --- 탭 4: 비밀의 방 (특수 관리 모드) ---
with tab4:
    if st.text_input("아빠 비밀번호", type="password") == "love317619":
        st.subheader("🔒 시크릿 관리소")
        m_tab1, m_tab2, m_tab3 = st.tabs(["🚨 학교 오답 관리", "📝 시험 단어 관리", "💣 전체 초기화"])
        
        with m_tab1:
            wrong_list = df[df['학교오답'] == "O"]
            st.write(f"현재 학교에서 틀린 단어: {len(wrong_list)}개")
            st.dataframe(wrong_list[['영어', '한글', '상태']])
            if st.button("🚨 학교 오답만 전부 다시 공부하기(상태 0)"):
                df.loc[df['학교오답'] == "O", '상태'] = 0
                conn.update(data=df); st.success("초기화 완료!"); st.rerun()
        
        with m_tab2:
            test_list = df[df['시험용'] == "O"]
            st.write(f"현재 시험용 단어: {len(test_list)}개")
            st.dataframe(test_list[['영어', '한글', '등록일']])
            if st.button("🗑️ 시험 끝! 시험 단어만 삭제하기"):
                df = df[df['시험용'] != "O"]
                conn.update(data=df); st.success("삭제 완료!"); st.rerun()

        with m_tab3:
            if st.checkbox("위험: 모든 데이터를 삭제하시겠습니까?"):
                if st.button("전체 삭제 실행", type="primary"):
                    conn.update(data=pd.DataFrame(columns=required_cols))
                    st.success("초기화되었습니다."); st.rerun()
