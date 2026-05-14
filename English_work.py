import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from gtts import gTTS
import io
from datetime import datetime

# 1. UI 설정 (연분홍 배경 + 진보라 폰트)
st.set_page_config(page_title="고은이의 마법 단어장", layout="centered")
st.markdown("""
<style>
    .stApp { background-color: #FFF0F5 !important; }
    h1, h2, h3, p, span, div, label, li, td, th { color: #4B0082 !important; font-weight: bold !important; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #9370DB !important; color: white !important; font-weight: bold; height: 3.5em; }
</style>
""", unsafe_allow_html=True)

st.title("💖 고은이의 마법 단어장 PRO")

# 오늘의 미션 세션 초기화
if 'today_score' not in st.session_state:
    st.session_state.today_score = 0
mission_goal = 5 # 하루 5개 맞히기 미션

# 2. 구글 시트 연결 및 데이터 준비
conn = st.connection("gsheets", type=GSheetsConnection)
try:
    df = conn.read(ttl=0)
    # 필수 컬럼(기둥)이 없으면 자동 생성
    required_cols = ['영어', '한글', '상태', '학교오답', '등록일']
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""
    
    # 데이터 정리
    df['상태'] = pd.to_numeric(df['상태'], errors='coerce').fillna(0).astype(int)
    # 공부할 단어(상태 4 미만)
    targets = df[df['상태'] < 4]
except Exception as e:
    st.error("🚨 구글 시트를 불러오는 중 에러가 발생했습니다.")
    st.stop()

# --- 오늘의 진도 미션 바 ---
st.info(f"🚩 오늘의 진도 미션: 퀴즈 {mission_goal}개 맞히기! (현재: {st.session_state.today_score}개 완료)")
if st.session_state.today_score >= mission_goal:
    st.success("🎉 오늘 미션 달성 완료! 고은이 최고야! 👑")

# 3. 대망의 4탭 구성
tab1, tab2, tab3, tab4 = st.tabs(["📖 단어학습", "🎯 마법퀴즈", "➕ 단어추가", "🔒 비밀의 방"])

# ==========================================
# 탭 1: 단어학습
# ==========================================
with tab1:
    if len(targets) > 0:
        if 'f_idx' not in st.session_state: st.session_state.f_idx = 0
        row = targets.iloc[st.session_state.f_idx % len(targets)]
        
        # 학교 오답인 경우 강조 뱃지
        badge = "🚨 학교에서 틀린 단어!" if str(row['학교오답']) == "O" else "✨"
        
        st.markdown(f"""
        <div style='background:white; padding:40px; border-radius:30px; border:5px solid #FFB6C1; text-align:center;'>
            <p style='color:#FF4500; font-size:20px; margin:0;'>{badge}</p>
            <h1 style='font-size:70px; margin-top:10px;'>{row['영어']}</h1>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔊 발음 듣기"):
                tts = gTTS(text=str(row['영어']), lang='en')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp, format='audio/mp3')
        with col2:
            if st.button("뜻 보기 / 다음 ➡️"):
                st.info(f"💡 뜻: {row['한글']}")
                st.session_state.f_idx += 1
                time.sleep(1.5)
                st.rerun()
    else:
        st.success("단어장에 공부할 단어가 없어요!")

# ==========================================
# 탭 2: 마법퀴즈
# ==========================================
with tab2:
    if len(targets) > 0:
        if 'q_word' not in st.session_state:
            # 학교 오답을 우선적으로 출제하는 로직 아이디어 적용 가능 (여기선 랜덤 출제)
            st.session_state.q_word = targets.sample(1).iloc[0]
            
        q = st.session_state.q_word
        badge_q = "🚨 집중!" if str(q['학교오답']) == "O" else "✨"
        
        st.markdown(f"<div style='text-align:center;'><h3>{badge_q} 이 단어의 뜻은?</h3><h1 style='font-size:60px;'>{q['영어']}</h1></div>", unsafe_allow_html=True)
        
        ans = st.text_input("정답 입력", key="quiz_input").strip()
        if st.button("정답 확인! 🚀"):
            if ans == str(q['한글']).strip():
                # 상태 업데이트 및 미션 카운트
                idx = df[df['영어'] == q['영어']].index[0]
                df.at[idx, '상태'] += 1
                conn.update(data=df)
                
                st.session_state.today_score += 1
                st.balloons()
                st.success("천재! 정답이야! 💖")
                del st.session_state.q_word
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("앗! 다시 한번 생각해볼까? 💪")
    else:
        st.write("퀴즈를 풀 단어가 없습니다.")

# ==========================================
# 탭 3: 단어추가 (학교 오답 체크 기능)
# ==========================================
with tab3:
    st.header("📝 새로운 단어 넣기")
    with st.form("add_form", clear_on_submit=True):
        new_eng = st.text_input("영어 단어 (예: apple)")
        new_kor = st.text_input("한글 뜻 (예: 사과)")
        is_school_wrong = st.checkbox("🏫 학교에서 틀렸던 단어예요! (체크 시 퀴즈 우선/강조)")
        
        if st.form_submit_button("단어장에 저장하기 💾"):
            if new_eng and new_kor:
                today_str = datetime.today().strftime('%Y-%m-%d')
                school_mark = "O" if is_school_wrong else "X"
                
                new_row = pd.DataFrame([{
                    "영어": new_eng, "한글": new_kor, "상태": 0, 
                    "학교오답": school_mark, "등록일": today_str
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.success(f"'{new_eng}' 단어 추가 완료! 시트에 저장되었습니다.")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("단어와 뜻을 모두 적어주세요.")

# ==========================================
# 탭 4: 비밀의 방 (데이터 삭제 및 관리)
# ==========================================
with tab4:
    if st.text_input("아빠 전용 비밀번호", type="password") == "love317619":
        st.write("### 🛠️ 데이터 관리 (주의해서 사용하세요)")
        
        if not df.empty:
            # 1. 개별 삭제
            with st.expander("🗑️ 개별 단어 삭제"):
                del_word = st.selectbox("삭제할 단어 선택", df['영어'].tolist())
                if st.button("선택한 단어 삭제"):
                    df = df[df['영어'] != del_word]
                    conn.update(data=df)
                    st.success(f"'{del_word}' 삭제 완료!")
                    time.sleep(1)
                    st.rerun()
                    
            # 2. 일별 삭제
            with st.expander("📅 일별 단어 삭제 (특정 날짜에 추가한 단어 모두 삭제)"):
                dates = df['등록일'].dropna().unique().tolist()
                if dates:
                    del_date = st.selectbox("삭제할 날짜 선택", dates)
                    if st.button("해당 날짜 단어 모두 삭제"):
                        df = df[df['등록일'] != del_date]
                        conn.update(data=df)
                        st.success(f"{del_date}에 등록된 단어가 모두 삭제되었습니다.")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.write("등록일 정보가 있는 단어가 없습니다.")
                    
            # 3. 전체 삭제
            with st.expander("💣 전체 단어 삭제 (초기화)"):
                st.warning("정말로 모든 단어를 지우시겠습니까? 복구할 수 없습니다.")
                confirm_delete = st.checkbox("네, 모두 지우는 것에 동의합니다.")
                if confirm_delete and st.button("전체 삭제 실행", type="primary"):
                    empty_df = pd.DataFrame(columns=required_cols)
                    conn.update(data=empty_df)
                    st.success("모든 단어가 삭제되었습니다.")
                    time.sleep(1)
                    st.rerun()
                    
            st.write("---")
            st.write("📊 현재 시트 데이터 미리보기")
            st.dataframe(df)
        else:
            st.info("현재 단어장에 저장된 단어가 없습니다.")
