import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
import random
from gtts import gTTS
import io
from datetime import datetime
import calendar

# ==========================================
# 1. UI 설정 및 상태 관리 초기화
# ==========================================
st.set_page_config(page_title="영단어 암기 App(SGE)", layout="centered")
st.markdown("""
<style>
    .stApp { background-color: #FFF0F5 !important; }
    h1, h2, h3, p, span, div, label, li, td, th { color: #4B0082 !important; font-family: 'Apple SD Gothic Neo', sans-serif !important; font-weight: bold !important; }
    .stButton>button { width: 100%; border-radius: 15px; background: linear-gradient(135deg, #9370DB, #8A2BE2) !important; color: white !important; font-weight: bold; height: 3.5em; box-shadow: 0px 4px 6px rgba(0,0,0,0.2); margin-bottom: 5px; }
    .flashcard { background: white; padding: 50px 20px; border-radius: 30px; border: 4px solid #FFB6C1; text-align: center; margin-bottom: 25px; box-shadow: 0px 10px 20px rgba(255,182,193,0.4); }
    .stProgress > div > div > div > div { background-color: #9370DB !important; }
</style>
""", unsafe_allow_html=True)

st.title("💖 영단어 암기 App(SGE)")

# --- 상태 변수 초기화 ---
if 'test_active' not in st.session_state: st.session_state.test_active = False
if 'force_review' not in st.session_state: st.session_state.force_review = False
if 'show_meaning' not in st.session_state: st.session_state.show_meaning = False
if 'show_example' not in st.session_state: st.session_state.show_example = False
if 'f_idx' not in st.session_state: st.session_state.f_idx = 0
if 'quiz_pool' not in st.session_state: st.session_state.quiz_pool = []
if 'quiz_stats' not in st.session_state: st.session_state.quiz_stats = {'total': 0, 'correct': 0, 'is_school_quiz': False}

# ==========================================
# 2. 구글 시트 고속 메모리 연동 (오류 완벽 차단 기법)
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

# 앱의 메모리(session_state)에 단어 데이터가 없을 때만 딱 한 번 구글에서 읽어옵니다.
if 'main_df' not in st.session_state:
    try:
        loaded_df = conn.read(ttl=0)
        required_cols = ['영어', '한글', '상태', '학교학원', '레벨', '등록일', '최근학습일', '예문']
        for col in required_cols:
            if col not in loaded_df.columns: loaded_df[col] = ""
            
        loaded_df['상태'] = pd.to_numeric(loaded_df['상태'], errors='coerce').fillna(0).astype(int)
        today_str = datetime.today().strftime('%Y-%m-%d')
        loaded_df['등록일'] = loaded_df['등록일'].fillna(today_str).replace("", today_str)
        loaded_df['레벨'] = loaded_df['레벨'].fillna('중등').replace("", '중등')
        
        # 메모리에 안전하게 저장
        st.session_state.main_df = loaded_df
    except Exception as e:
        st.error(f"🚨 구글 시트 연결에 실패했습니다. 인터넷 연결이나 시트 설정을 확인해주세요. (원인: {e})")
        st.stop()

# 이제 앱은 구글 서버를 매번 찌르지 않고 메모리에 저장된 데이터를 초고속으로 읽습니다.
df = st.session_state.main_df
today_str = datetime.today().strftime('%Y-%m-%d')

# ==========================================
# 3. 사이드바 (레벨, 진도 및 수동 동기화 버튼)
# ==========================================
selected_level = st.sidebar.selectbox("🎯 학습 레벨 선택", ["중등", "고등"])
level_df = df[df['레벨'] == selected_level]

total_cnt = len(level_df)
master_cnt = len(level_df[level_df['상태'] >= 4])
progress = (master_cnt / total_cnt) if total_cnt > 0 else 0

st.sidebar.write(f"### {selected_level} 마스터 진도")
st.sidebar.progress(progress)
st.sidebar.write(f"{master_cnt} / {total_cnt} 완료")

st.sidebar.write("---")
if st.sidebar.button("🔄 구글시트 강제 동기화", help="구글 시트에서 직접 단어를 수정했을 때 눌러주세요."):
    if 'main_df' in st.session_state:
        del st.session_state.main_df
    st.rerun()

# ==========================================
# 4. 5대 핵심 탭 구성
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["👀 일반 깜빡이", "🏫 학교/학원 깜빡이", "🎯 실전 퀴즈", "➕ 단어 추가", "🔒 비밀의 방"])

# --- 공통 함수: 깜빡이 학습 ---
def run_flashcard(target_list, mode_name):
    if st.session_state.test_active:
        st.warning(f"⚠️ 시험 중에는 단어를 볼 수 없어요!")
        return

    if st.session_state.force_review and mode_name == "일반 단어":
        st.error("🚨 이전 시험에서 80점 미만을 받았어요! 다시 철저하게 복습하세요! 🚨")

    # 아빠의 기획: 딱 30개 단위로 끊어서 학습
    target_list = target_list.head(30)

    if target_list.empty:
        st.success(f"🎊 {mode_name}에 공부할 단어가 없어요!")
        return

    # 학습 완료 안내 창
    if st.session_state.f_idx >= len(target_list):
        st.session_state.force_review = False
        st.markdown(f"<div class='flashcard'><h2>🎉 {mode_name} {len(target_list)}개 학습 완료!</h2><p>목표량을 다 채웠어요! 이제 무엇을 할까요?</p></div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 처음부터 반복 학습하기", key=f"replay_{mode_name}"):
                st.session_state.f_idx = 0
                st.rerun()
        with col2:
            if st.button("✍️ 실전 퀴즈 모드로 가기", key=f"go_quiz_{mode_name}"):
                st.session_state.test_active = True
                st.session_state.f_idx = 0
                st.rerun()
        return

    row = target_list.iloc[st.session_state.f_idx]
    reg_date = datetime.strptime(str(row['등록일']), '%Y-%m-%d')
    is_recent = (datetime.today() - reg_date).days <= 7
    badge = "🔥 집중 복습!" if is_recent else "✨ 학습 중"
    
    st.markdown(f"<div class='flashcard'><p style='color:red;'>{badge} [{mode_name}] ( {st.session_state.f_idx + 1} / {len(target_list)} )</p><h1 style='font-size:70px;'>{row['영어']}</h1></div>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔊 발음 듣기", key=f"audio_{mode_name}"):
            tts = gTTS(text=str(row['영어']), lang='en')
            fp = io.BytesIO(); tts.write_to_fp(fp); st.audio(fp, format='audio/mp3')
    with c2:
        if st.button("💡 뜻 보기/가리기", key=f"toggle_{mode_name}"):
            st.session_state.show_meaning = not st.session_state.show_meaning

    if st.button("📖 예문 보기/가리기", key=f"ex_btn_{mode_name}"):
        st.session_state.show_example = not st.session_state.show_example
    
    if st.session_state.show_meaning: st.success(f"정답: {row['한글']}")
    if st.session_state.show_example:
        ex_text = row['예문'] if pd.notna(row['예문']) and str(row['예문']).strip() != "" else "등록된 예문이 없습니다."
        st.info(f"📝 예문: {ex_text}")
    if not st.session_state.show_meaning and not st.session_state.show_example:
        st.write("<div style='height: 58px;'></div>", unsafe_allow_html=True)
    
    if st.button("➡️ 다음 단어로", key=f"next_{mode_name}"):
        st.session_state.show_meaning = False
        st.session_state.show_example = False
        st.session_state.f_idx += 1
        st.rerun()

# --- 탭 1: 일반 깜빡이 ---
with tab1:
    general_unmastered = level_df[(level_df['상태'] < 4) & (level_df['학교학원'] != "O")].reset_index(drop=True)
    run_flashcard(general_unmastered, "일반 단어")

# --- 탭 2: 학교/학원 깜빡이 ---
with tab2:
    school_unmastered = level_df[(level_df['상태'] < 4) & (level_df['학교학원'] == "O")].reset_index(drop=True)
    run_flashcard(school_unmastered, "학교/학원")

# --- 탭 3: 실전 퀴즈 ---
with tab3:
    if not st.session_state.test_active:
        st.write("### 어떤 시험을 볼까요?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✍️ 일반 단어 시험 시작"):
                st.session_state.test_active = True
                quiz_targets = general_unmastered.head(30)
                st.session_state.quiz_pool = quiz_targets.to_dict('records')
                random.shuffle(st.session_state.quiz_pool)
                st.session_state.quiz_stats = {'total': len(quiz_targets), 'correct': 0, 'is_school_quiz': False}
                st.session_state.q_done = False
                st.rerun()
        with c2:
            if st.button("🏫 학교/학원 시험 시작"):
                st.session_state.test_active = True
                quiz_targets = school_unmastered.head(30)
                st.session_state.quiz_pool = quiz_targets.to_dict('records')
                random.shuffle(st.session_state.quiz_pool)
                st.session_state.quiz_stats = {'total': len(quiz_targets), 'correct': 0, 'is_school_quiz': True}
                st.session_state.q_done = False
                st.rerun()
    
    if st.session_state.test_active:
        if st.session_state.quiz_pool:
            q = st.session_state.quiz_pool[0]
            current_q_num = st.session_state.quiz_stats['total'] - len(st.session_state.quiz_pool) + 1
            
            st.markdown(f"<div class='flashcard'><h3>Q{current_q_num}. 뜻을 맞혀보세요!</h3><h1 style='font-size:60px;'>{q['영어']}</h1></div>", unsafe_allow_html=True)
            
            if not st.session_state.q_done:
                ans = st.text_input("정답 입력", key=f"q_{q['영어']}").strip()
                if st.button("정답 확인 🚀"):
                    st.session_state.q_done = True
                    raw_answer = str(q['한글'])
                    correct_list = [c.strip() for c in raw_answer.replace('/', ',').split(',')]
                    
                    df_idx = df[df['영어'] == q['영어']].index[0]
                    
                    if ans in correct_list:
                        st.session_state.q_res = True
                        st.session_state.quiz_stats['correct'] += 1
                        df.at[df_idx, '상태'] = int(df.at[df_idx, '상태']) + 1
                        df.at[df_idx, '최근학습일'] = today_str
                    else: 
                        st.session_state.q_res = False
                        df.at[df_idx, '상태'] = 0
                        df.at[df_idx, '등록일'] = today_str
                        
                    # 메모리와 구글시트를 동시에 업데이트
                    st.session_state.main_df = df
                    conn.update(data=df)
                    st.rerun()
            else:
                if st.session_state.q_res: 
                    st.balloons(); st.success(f"🎉 정답이야! (등록된 뜻: {q['한글']})")
                else: 
                    st.error(f"오답! 정답은 '{q['한글']}' (이)야. (내일 복습에 자동 추가됨!)")
                
                if st.button("➡️ 다음 문제"):
                    st.session_state.quiz_pool.pop(0)
                    st.session_state.q_done = False
                    st.rerun()
            
            st.write("---")
            if st.button("🏁 시험 강제 종료"):
                st.session_state.test_active = False
                st.session_state.quiz_pool = []
                st.rerun()
                
        else:
            total = st.session_state.quiz_stats['total']
            correct = st.session_state.quiz_stats['correct']
            score = int((correct / total * 100)) if total > 0 else 0
            
            st.markdown(f"<div class='flashcard'><h2>🏁 시험 종료!</h2><h1>{score} 점</h1><p>{total}문제 중 {correct}문제 정답</p></div>", unsafe_allow_html=True)
            
            if score < 80 and not st.session_state.quiz_stats['is_school_quiz']:
                st.error("🚨 80점 미만이므로 [일반 깜빡이] 탭으로 돌아가 다시 복습해야 합니다!")
                if st.button("😭 알겠습니다 (학습 탭으로 이동)"):
                    st.session_state.force_review = True
                    st.session_state.test_active = False
                    st.session_state.f_idx = 0
                    st.rerun()
            else:
                if score >= 80: st.success("🎉 80점 이상 통과! 참 잘했어요!")
                else: st.info("학교/학원 단어 시험 수고했어요!")
                
                if st.button("🏠 메인으로 가기"):
                    st.session_state.test_active = False
                    st.rerun()

# --- 탭 4: 단어 추가 ---
with tab4:
    st.header("➕ 단어 추가 (SGE)")
    with st.form("new_add", clear_on_submit=True):
        eng = st.text_input("영어 단어 (필수)")
        kor = st.text_input("한글 뜻 (여러 개일 경우 쉼표로 구분. 예: 사과, 사과하다)")
        ex_sentence = st.text_area("예문 (선택 사항)")
        lv = st.radio("레벨", ["중등", "고등"], horizontal=True)
        is_school = st.checkbox("🏫 학교/학원 단어장용 (체크 시 전용 탭으로 분류)")
        
        if st.form_submit_button("저장하기 💾"):
            if eng and kor:
                new_row = pd.DataFrame([{"영어": eng, "한글": kor, "상태": 0, "학교학원": "O" if is_school else "X", "레벨": lv, "등록일": today_str, "최근학습일": "", "예문": ex_sentence}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                
                # 메모리와 구글시트 동시 업데이트
                st.session_state.main_df = updated_df
                conn.update(data=updated_df)
                
                st.success("저장 완료!")
                time.sleep(1); st.rerun()
            else: st.warning("영어 단어와 한글 뜻은 꼭 적어주세요!")

# --- 탭 5: 비밀의 방 ---
with tab5:
    if st.text_input("아빠 비밀번호", type="password") == "love317619":
        st.subheader("🔒 아빠의 관리소")
        m_tab1, m_tab2 = st.tabs(["📅 학습 캘린더", "💣 데이터 정리"])
        
        with m_tab1:
            studied_dates = set(df['최근학습일'].dropna().replace("", pd.NA).dropna().tolist())
            now = datetime.now()
            cal = calendar.Calendar(firstweekday=6)
            month_days = cal.monthdatescalendar(now.year, now.month)
            cal_html = "<table style='width:100%; text-align:center; border-collapse: collapse; font-size: 18px;'><tr style='background-color:#9370DB; color:white;'><th>일</th><th>월</th><th>화</th><th>수</th><th>목</th><th>금</th><th>토</th></tr>"
            for week in month_days:
                cal_html += "<tr>"
                for d in week:
                    d_str = d.strftime('%Y-%m-%d')
                    if d.month == now.month:
                        if d_str in studied_dates: cal_html += f"<td style='padding:15px; border:1px solid #FFB6C1; background-color:#FFF0F5;'>🟢<br><b>{d.day}</b></td>"
                        else: cal_html += f"<td style='padding:15px; border:1px solid #ddd;'>{d.day}</td>"
                    else: cal_html += "<td style='padding:15px; border:1px solid #ddd; color:#ccc;'></td>"
                cal_html += "</tr>"
            cal_html += "</table>"
            st.markdown(cal_html, unsafe_allow_html=True)
            
        with m_tab2:
            st.dataframe(df)
            if st.button("💣 전체 데이터 초기화"):
                empty_df = pd.DataFrame(columns=required_cols)
                st.session_state.main_df = empty_df
                conn.update(data=empty_df)
                st.success("초기화 완료!"); st.rerun()
