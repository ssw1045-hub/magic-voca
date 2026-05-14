import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from gtts import gTTS
import io
from datetime import datetime

# ==========================================
# 1. 완벽한 UI/UX 인테리어 (입체 버튼 & 플래시카드)
# ==========================================
st.set_page_config(page_title="고은이의 마법 단어장", layout="centered")
st.markdown("""
<style>
    /* 전체 배경 */
    .stApp { background-color: #FFF0F5 !important; }
    
    /* 폰트 색상 및 굵기 */
    h1, h2, h3, p, span, div, label, li, td, th { 
        color: #4B0082 !important; 
        font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif !important; 
        font-weight: bold !important; 
    }
    
    /* 🚀 메인 버튼 입체 디자인 */
    .stButton>button { 
        width: 100%; border-radius: 15px; 
        background: linear-gradient(135deg, #9370DB, #8A2BE2) !important; 
        color: white !important; font-weight: bold; font-size: 16px; 
        height: 3.5em; border: none; 
        box-shadow: 0px 4px 6px rgba(0,0,0,0.2); transition: all 0.2s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0px 6px 12px rgba(0,0,0,0.3);
    }
    
    /* 🃏 고급 플래시카드 디자인 */
    .flashcard { 
        background: white; padding: 60px 20px; border-radius: 30px; 
        border: 4px solid #FFB6C1; text-align: center; margin-bottom: 25px; 
        box-shadow: 0px 10px 20px rgba(255,182,193,0.4); 
    }
    
    /* 입력창 및 탭 스타일 */
    input { color: #000 !important; font-size: 18px !important; text-align: center; }
    .stTabs [data-baseweb="tab"] p { font-size: 18px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("💖 고은이의 마법 단어장 PRO")

# ==========================================
# 2. 데이터 불러오기 및 기본 세팅
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
try:
    df = conn.read(ttl=0)
    
    # 필수 기둥(컬럼) 확인
    required_cols = ['영어', '한글', '상태', '학교오답', '등록일']
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""
            
    df['상태'] = pd.to_numeric(df['상태'], errors='coerce').fillna(0).astype(int)
    
    # 빈 등록일은 오늘 날짜로 채우기
    today_str = datetime.today().strftime('%Y-%m-%d')
    df['등록일'] = df['등록일'].fillna(today_str).replace("", today_str)
    
    # 아직 다 못 외운 단어들만 모으기
    unmastered = df[df['상태'] < 4].reset_index(drop=True)
except Exception as e:
    st.error("🚨 구글 시트 연결 에러! 공유 설정과 주소를 확인해주세요.")
    st.stop()

# ==========================================
# 3. 대치동 7일 누적 + 주차별 스와이프 알고리즘
# ==========================================
if not unmastered.empty:
    # 최초 등록일을 기준으로 몇 일차인지 계산 (오늘부터 시작이면 1일차)
    start_date_str = unmastered['등록일'].min()
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        days_passed = (datetime.today() - start_date).days
        if days_passed < 0: days_passed = 0
    except:
        days_passed = 0
        
    day_number = days_passed + 1
    week = (day_number - 1) // 7 + 1
    day_of_week = (day_number - 1) % 7 + 1 # 1(월요일 역할) ~ 7(일요일 역할)
    
    # 주차별 누적 로직 (1주 = 210개 기준)
    prev_week_start = max(0, (week - 2) * 210) # 1주차일땐 0, 2주차일땐 0, 3주차일땐 210
    
    curr_week_start = (week - 1) * 210
    curr_week_end = curr_week_start + (day_of_week * 30) # 매일 30개씩 추가
    
    # 7일차(일요일)는 이번주 210개 전체 복습
    if day_of_week == 7:
        curr_week_end = curr_week_start + 210
        
    # 최종 오늘 공부할 타겟 범위 (이전 주차 + 이번 주 누적)
    today_targets = unmastered.iloc[prev_week_start:curr_week_end]
    
    if day_of_week < 7:
        msg = f"오늘은 {week}주차 {day_of_week}일째! 총 {len(today_targets)}개 누적 학습일이에요 📚"
    else:
        msg = f"오늘은 {week}주차 총복습일! ({len(today_targets)}개) 시험을 쳐볼까요? 👑"
else:
    today_targets = pd.DataFrame()
    msg = "단어장에 공부할 단어가 없어요! 단어를 추가해주세요."

st.info(f"📅 {msg}")

# ==========================================
# 4. 직관적인 4탭 구성
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["📖 깜빡이 학습", "🎯 마법 퀴즈", "➕ 단어 추가", "🔒 비밀의 방"])

# --- 탭 1: 깜빡이 학습 (수동 제어) ---
with tab1:
    if len(today_targets) > 0:
        if 'f_idx' not in st.session_state: st.session_state.f_idx = 0
        idx = st.session_state.f_idx % len(today_targets)
        row = today_targets.iloc[idx]
        
        badge = "🚨 학교 오답!" if str(row['학교오답']) == "O" else "✨ 집중!"
        
        st.markdown(f"<div class='flashcard'><p style='color:#FF4500; font-size:20px; margin:0;'>{badge}</p><h1 style='font-size:80px; margin:10px 0;'>{row['영어']}</h1></div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔊 발음 듣기", key=f"audio_{idx}"):
                tts = gTTS(text=str(row['영어']), lang='en')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp, format='audio/mp3')
        with col2:
            if st.button("💡 뜻 보기", key=f"mean_{idx}"):
                st.success(f"정답: {row['한글']}")
                
        if st.button("➡️ 다음 단어로 넘어가기", key=f"next_{idx}"):
            st.session_state.f_idx += 1
            st.rerun()
    else:
        st.success("오늘 분량을 모두 마스터했어요! 👑")

# --- 탭 2: 마법 퀴즈 (답답함 완전 해소!) ---
with tab2:
    if len(today_targets) > 0:
        if 'q_word' not in st.session_state:
            st.session_state.q_word = today_targets.sample(1).iloc[0]
            st.session_state.q_answered = False
            
        q = st.session_state.q_word
        badge_q = "🚨 학교 오답!" if str(q['학교오답']) == "O" else "✨"
        
        st.markdown(f"<div class='flashcard'><p style='color:#FF4500; font-size:20px; margin:0;'>{badge_q}</p><h3>이 단어의 뜻은?</h3><h1 style='font-size:70px;'>{q['영어']}</h1></div>", unsafe_allow_html=True)
        
        # 문제 푸는 중
        if not st.session_state.q_answered:
            ans = st.text_input("정답 입력", key=f"quiz_in_{q['영어']}").strip()
            
            if st.button("정답 확인! 🚀"):
                st.session_state.q_answered = True
                if ans == str(q['한글']).strip():
                    st.session_state.q_correct = True
                    # 정답 시 구글 시트 업데이트
                    df_idx = df[df['영어'] == q['영어']].index[0]
                    df.at[df_idx, '상태'] += 1
                    conn.update(data=df)
                else:
                    st.session_state.q_correct = False
                st.rerun()
                
        # 결과 확인 후 수동으로 넘어가기
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

# --- 탭 3: 단어 추가 ---
with tab3:
    st.header("📝 새로운 단어 넣기")
    with st.form("add_form", clear_on_submit=True):
        new_eng = st.text_input("영어 단어 (예: apple)")
        new_kor = st.text_input("한글 뜻 (예: 사과)")
        is_school_wrong = st.checkbox("🏫 학교/문제집에서 틀렸던 단어예요! (체크 시 🚨 뱃지 추가)")
        
        if st.form_submit_button("단어장에 저장하기 💾"):
            if new_eng and new_kor:
                school_mark = "O" if is_school_wrong else "X"
                new_row = pd.DataFrame([{"영어": new_eng, "한글": new_kor, "상태": 0, "학교오답": school_mark, "등록일": today_str}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.success(f"'{new_eng}' 단어 추가 완료! 시트에 저장되었습니다.")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("단어와 뜻을 모두 적어주세요.")

# --- 탭 4: 비밀의 방 (안전한 관리 모드 복구) ---
with tab4:
    if st.text_input("아빠 전용 비밀번호", type="password") == "love317619":
        st.write("### 🛠️ 데이터 관리 (주의해서 사용하세요)")
        
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
                # 안전한 날짜 추출
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
                    
            with st.expander("💣 전체 단어 삭제 (초기화)"):
                st.warning("정말로 모든 단어를 지우시겠습니까? 복구할 수 없습니다.")
                if st.checkbox("네, 모두 지우는 것에 동의합니다."):
                    if st.button("전체 삭제 실행", type="primary"):
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
