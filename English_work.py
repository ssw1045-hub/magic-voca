import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from gtts import gTTS
import io
from datetime import datetime

# 1. 완벽한 파스텔 감성 & 직관적 UI/UX 복구
st.set_page_config(page_title="고은이의 마법 단어장", layout="centered")
st.markdown("""
<style>
    .stApp { background-color: #FFF0F5 !important; }
    h1, h2, h3, p, span, div, label, li, td, th { color: #4B0082 !important; font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif !important; font-weight: bold !important; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #9370DB !important; color: white !important; font-weight: bold; height: 3.5em; font-size: 16px; margin-top: 5px; }
    /* 단어 카드 디자인 */
    .flashcard { background: white; padding: 50px; border-radius: 30px; border: 5px solid #FFB6C1; text-align: center; margin-bottom: 20px; box-shadow: 0px 5px 15px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

st.title("💖 고은이의 마법 단어장 PRO")

# 2. 구글 시트 연결 및 데이터 준비
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
    
    # 필수 기둥 생성
    required_cols = ['영어', '한글', '상태', '학교오답', '등록일']
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""
            
    df['상태'] = pd.to_numeric(df['상태'], errors='coerce').fillna(0).astype(int)
    # 아직 완벽히 마스터(👑)하지 못한 단어들
    unmastered = df[df['상태'] < 4]
    
except Exception as e:
    st.error("구글 시트를 불러오지 못했습니다. 설정을 확인해주세요.")
    st.stop()

# 3. 요일별 누적 알고리즘 (월=1, 화=2 ... 일=7)
weekday = datetime.today().weekday() + 1
week_pool = unmastered.head(210) # 1주일간 다룰 최대 210개

if weekday < 7:
    # 월~토: 요일 일수 * 30개 누적 배정
    today_targets = week_pool.head(weekday * 30)
    msg = f"오늘은 {weekday}일차! 총 {len(today_targets)}개 단어 누적 학습일이에요. (오늘 신규 + 지난 복습)"
else:
    # 일요일: 이번 주 풀세트 총망라
    today_targets = week_pool 
    msg = f"오늘은 일요일! 이번 주 배운 전체 단어({len(today_targets)}개) 총복습 시험일이에요 👑"

st.info(f"📅 {msg}")

# 4. 직관적인 4탭 분리
tab1, tab2, tab3, tab4 = st.tabs(["📖 깜빡이 학습", "🎯 오늘의 시험", "➕ 단어 추가", "🔒 비밀의 방"])

# ==========================================
# 탭 1: 깜빡이 학습 (자동 넘어가기 삭제, 수동 제어)
# ==========================================
with tab1:
    if len(today_targets) > 0:
        if 'f_idx' not in st.session_state: st.session_state.f_idx = 0
        idx = st.session_state.f_idx % len(today_targets)
        row = today_targets.iloc[idx]
        
        badge = "🚨 학교 오답!" if str(row['학교오답']) == "O" else "✨"
        
        st.markdown(f"<div class='flashcard'><p style='color:#FF4500; font-size:20px; margin:0;'>{badge}</p><h1 style='font-size:70px;'>{row['영어']}</h1></div>", unsafe_allow_html=True)
        
        # 버튼을 3개로 직관적으로 나열
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔊 발음 듣기", key=f"audio_{idx}"):
                tts = gTTS(text=str(row['영어']), lang='en')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp, format='audio/mp3')
        with col2:
            if st.button("💡 뜻 보기", key=f"mean_{idx}"):
                st.success(f"정답: {row['한글']}")
        with col3:
            if st.button("➡️ 다음 단어", key=f"next_{idx}"):
                st.session_state.f_idx += 1
                st.rerun()
    else:
        st.success("이번 주에 학습할 단어가 모두 마스터되었어요! 👑")

# ==========================================
# 탭 2: 마법 퀴즈 (답답함 해소! 직접 확인 후 넘어가기)
# ==========================================
with tab2:
    if len(today_targets) > 0:
        if 'q_word' not in st.session_state:
            st.session_state.q_word = today_targets.sample(1).iloc[0]
            st.session_state.q_answered = False
            st.session_state.q_correct = False
            
        q = st.session_state.q_word
        badge_q = "🚨 집중!" if str(q['학교오답']) == "O" else "✨"
        
        st.markdown(f"<div class='flashcard'><p style='color:#FF4500; font-size:20px; margin:0;'>{badge_q}</p><h3>이 단어의 뜻은?</h3><h1 style='font-size:60px;'>{q['영어']}</h1></div>", unsafe_allow_html=True)
        
        # 문제를 아직 안 풀었을 때 (입력창 나옴)
        if not st.session_state.q_answered:
            ans = st.text_input("정답 입력", key=f"quiz_in_{q['영어']}").strip()
            
            if st.button("정답 확인! 🚀"):
                st.session_state.q_answered = True
                if ans == str(q['한글']).strip():
                    st.session_state.q_correct = True
                    df_idx = df[df['영어'] == q['영어']].index[0]
                    df.at[df_idx, '상태'] += 1
                    conn.update(data=df)
                else:
                    st.session_state.q_correct = False
                st.rerun()
                
        # 문제를 풀었을 때 (결과 보여주고 다음 버튼 나옴)
        else:
            if st.session_state.q_correct:
                st.balloons()
                st.success(f"🎉 천재! 정답이야! ('{q['한글']}')")
            else:
                st.error(f"앗! 틀렸어. 정답은 '{q['한글']}'(이)야. 다음에 꼭 맞추자! 💪")
                
            if st.button("➡️ 다음 문제로 넘어가기"):
                del st.session_state.q_word
                st.session_state.q_answered = False
                st.rerun()
    else:
        st.success("오늘 시험 볼 단어가 없습니다!")

# ==========================================
# 탭 3: 단어 추가 (오답 전용 체크 기능 유지)
# ==========================================
with tab3:
    st.header("📝 새로운 단어 넣기")
    with st.form("add_form", clear_on_submit=True):
        new_eng = st.text_input("영어 단어 (예: apple)")
        new_kor = st.text_input("한글 뜻 (예: 사과)")
        is_school_wrong = st.checkbox("🏫 학교/문제집에서 틀렸던 단어예요! (체크 시 🚨 뱃지 추가)")
        
        if st.form_submit_button("단어장에 저장하기 💾"):
            if new_eng and new_kor:
                today_str = datetime.today().strftime('%Y-%m-%d')
                school_mark = "O" if is_school_wrong else "X"
                new_row = pd.DataFrame([{"영어": new_eng, "한글": new_kor, "상태": 0, "학교오답": school_mark, "등록일": today_str}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.success(f"'{new_eng}' 단어 추가 완료!")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("단어와 뜻을 모두 적어주세요.")

# ==========================================
# 탭 4: 비밀의 방 (아빠 전용 삭제 및 관리)
# ==========================================
with tab4:
    if st.text_input("아빠 전용 비밀번호", type="password") == "love317619":
        st.write("### 🛠️ 데이터 관리 (주의!)")
        if not df.empty:
            with st.expander("🗑️ 개별 단어 삭제"):
                del_word = st.selectbox("삭제할 단어 선택", df['영어'].tolist())
                if st.button("선택한 단어 삭제"):
                    df = df[df['영어'] != del_word]
                    conn.update(data=df)
                    st.success(f"'{del_word}' 삭제 완료!")
                    time.sleep(1)
                    st.rerun()
                    
            with st.expander("📅 일별 단어 삭제"):
                dates = df['등록일'].dropna().unique().tolist()
                if dates:
                    del_date = st.selectbox("삭제할 날짜 선택", dates)
                    if st.button("해당 날짜에 등록된 단어 모두 삭제"):
                        df = df[df['등록일'] != del_date]
                        conn.update(data=df)
                        st.success(f"{del_date} 등록 단어 삭제 완료!")
                        time.sleep(1)
                        st.rerun()
                        
            with st.expander("💣 전체 단어 삭제 (초기화)"):
                if st.checkbox("네, 모두 지우는 것에 동의합니다."):
                    if st.button("전체 삭제 실행", type="primary"):
                        empty_df = pd.DataFrame(columns=required_cols)
                        conn.update(data=empty_df)
                        st.success("모든 단어가 삭제되었습니다.")
                        time.sleep(1)
                        st.rerun()
                        
            st.write("---")
            st.write("📊 현재 시트 데이터")
            st.dataframe(df)
        else:
            st.info("단어장에 저장된 단어가 없습니다.")
