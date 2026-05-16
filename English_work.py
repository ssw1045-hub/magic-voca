import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
import random
from gtts import gTTS
import io
from datetime import datetime
import calendar

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# ==========================================
# 🤖 AI 비서 API 키 영구 저장 (매우 중요 ⭐)
# 아래 따옴표 안에 발급받으신 Gemini API 키를 붙여넣으세요!
# ==========================================
MY_GEMINI_API_KEY = "여기에_아버님의_API키를_붙여넣으세요"

# ==========================================
# 🎁 아빠의 룰렛 선물 10가지
# ==========================================
default_prizes = [
    "💸 용돈 3,000원", "🍦 베스킨라빈스 싱글", "🍗 아빠가 쏘는 치킨!",
    "🎮 게임 1시간 이용권", "🎬 보고 싶은 영화 보기", "떡볶이 사먹기 찬스",
    "마라탕 쏘기!", "원하는 간식 1개 고르기", "휴식권 30분", "아빠의 폭풍 칭찬 및 안마"
]

# ==========================================
# 1. UI 설정 및 상태 관리
# ==========================================
st.set_page_config(page_title="영단어 암기 App(SGE)", layout="centered")
st.markdown("""
<style>
    .stApp { background-color: #FFF0F5 !important; }
    h1, h2, h3, p, span, div, label, li, td, th { color: #4B0082 !important; font-family: 'Apple SD Gothic Neo', sans-serif !important; font-weight: bold !important; }
    .stButton>button { width: 100%; border-radius: 15px; background: linear-gradient(135deg, #9370DB, #8A2BE2) !important; color: white !important; font-weight: bold; height: 3.5em; box-shadow: 0px 4px 6px rgba(0,0,0,0.2); margin-bottom: 5px; }
    .flashcard { background: white; padding: 50px 20px; border-radius: 30px; border: 4px solid #FFB6C1; text-align: center; margin-bottom: 25px; box-shadow: 0px 10px 20px rgba(255,182,193,0.4); }
    .roulette-box { background: #FFF8DC; padding: 40px; border-radius: 30px; border: 5px dashed #FFD700; text-align: center; margin: 20px 0; }
    .stProgress > div > div > div > div { background-color: #9370DB !important; }
</style>
""", unsafe_allow_html=True)

st.title("💖 영단어 암기 App(SGE)")

if 'test_active' not in st.session_state: st.session_state.test_active = False
if 'force_review' not in st.session_state: st.session_state.force_review = False
if 'show_meaning' not in st.session_state: st.session_state.show_meaning = False
if 'show_example' not in st.session_state: st.session_state.show_example = False
if 'f_idx' not in st.session_state: st.session_state.f_idx = 0
if 'quiz_pool' not in st.session_state: st.session_state.quiz_pool = []
if 'quiz_stats' not in st.session_state: st.session_state.quiz_stats = {'total': 0, 'correct': 0, 'is_school_quiz': False}
if 'spin_tickets' not in st.session_state: st.session_state.spin_tickets = 0
if 'prizes' not in st.session_state: st.session_state.prizes = default_prizes

# ==========================================
# 2. 구글 시트 데이터 로드
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
required_cols = ['영어', '한글', '상태', '학교학원', '레벨', '등록일', '최근학습일', '예문']

if 'main_df' not in st.session_state:
    try:
        loaded_df = conn.read(ttl=0)
        for col in required_cols:
            if col not in loaded_df.columns: loaded_df[col] = ""
            
        # 💡 [V28 업데이트] 빈칸이라도 무조건 텍스트(문자열)로 강제 인식시킴
        loaded_df['상태'] = pd.to_numeric(loaded_df['상태'], errors='coerce').fillna(0).astype(int)
        today_str = datetime.today().strftime('%Y-%m-%d')
        loaded_df['등록일'] = loaded_df['등록일'].fillna(today_str).replace("", today_str).astype(str)
        loaded_df['레벨'] = loaded_df['레벨'].fillna('중등').replace("", '중등').astype(str)
        loaded_df['예문'] = loaded_df['예문'].fillna("").astype(str)  # 강제 텍스트화 (에러 해결!)
        loaded_df['한글'] = loaded_df['한글'].fillna("").astype(str)
        loaded_df['최근학습일'] = loaded_df['최근학습일'].fillna("").astype(str)
        
        st.session_state.main_df = loaded_df
    except Exception as e:
        st.error(f"🚨 구글 시트 연결 실패! (원인: {e})")
        st.stop()

df = st.session_state.main_df

# ==========================================
# 3. 달력 기반 스케줄링 (일요일 시작)
# ==========================================
today_date = datetime.today()
today_str = today_date.strftime('%Y-%m-%d')
custom_weekday = (today_date.weekday() + 1) % 7 
week_days_custom = ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"]
today_name = week_days_custom[custom_weekday]
last_day_of_month = calendar.monthrange(today_date.year, today_date.month)[1]
is_last_day = (today_date.day == last_day_of_month)

selected_level = st.sidebar.selectbox("🎯 학습 레벨 선택", ["중등", "고등"])
level_df = df[df['레벨'] == selected_level]

total_cnt = len(level_df)
master_cnt = len(level_df[level_df['상태'] >= 4])
progress = (master_cnt / total_cnt) if total_cnt > 0 else 0

if is_last_day:
    study_limit = 9999 
    st.sidebar.error(f"🔥 오늘은 월말 총평가! 90점 이상 받고 룰렛 티켓을 노리세요!")
elif custom_weekday == 6: # 토요일
    study_limit = 180
    st.sidebar.success(f"👑 오늘은 {today_name}! 이번 주 총복습 및 시험일입니다.")
else:
    study_limit = (custom_weekday + 1) * 30
    st.sidebar.info(f"📅 오늘은 {today_name}! 누적 {study_limit}개 단어 학습일입니다.")

st.sidebar.write("---")
st.sidebar.progress(progress); st.sidebar.write(f"{master_cnt} / {total_cnt} 완료")
if st.sidebar.button("🔄 구글시트 강제 동기화"):
    if 'main_df' in st.session_state: del st.session_state.main_df
    st.rerun()

# ==========================================
# 4. 앱 본문 탭 구성
# ==========================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["👀 일반", "🏫 학교", "🎯 퀴즈", "🎁 룰렛", "➕ 추가", "🔒 비밀"])

def run_flashcard(target_list, mode_name, limit):
    if st.session_state.test_active:
        st.warning("⚠️ 시험 중에는 단어를 볼 수 없어요!"); return
    if st.session_state.force_review and mode_name == "일반 단어":
        st.error("🚨 이전 시험 80점 미만! 다시 철저하게 복습하세요! 🚨")

    target_list = target_list.head(limit)
    if target_list.empty: st.success(f"🎊 공부할 단어가 없어요!"); return

    if st.session_state.f_idx >= len(target_list):
        st.session_state.force_review = False
        msg = "월말 총복습 완료!" if is_last_day else f"{mode_name} 학습 완료!"
        st.markdown(f"<div class='flashcard'><h2>🎉 {msg}</h2></div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 처음부터 복습", key=f"r_{mode_name}"): st.session_state.f_idx = 0; st.rerun()
        with c2:
            if st.button("✍️ 퀴즈로 가기", key=f"q_{mode_name}"): st.session_state.test_active = True; st.session_state.f_idx = 0; st.rerun()
        return

    row = target_list.iloc[st.session_state.f_idx]
    reg_date = datetime.strptime(str(row['등록일']), '%Y-%m-%d')
    badge = "🔥 집중 복습!" if (datetime.today() - reg_date).days <= 7 else "✨ 학습 중"
    
    st.markdown(f"<div class='flashcard'><p style='color:red;'>{badge} ( {st.session_state.f_idx + 1} / {len(target_list)} )</p><h1 style='font-size:70px;'>{row['영어']}</h1></div>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔊 발음 듣기", key=f"a_{mode_name}"):
            tts = gTTS(text=str(row['영어']), lang='en'); fp = io.BytesIO(); tts.write_to_fp(fp); st.audio(fp, format='audio/mp3')
    with c2:
        if st.button("💡 뜻 보기/가리기", key=f"t_{mode_name}"): st.session_state.show_meaning = not st.session_state.show_meaning

    # ==============================================
    # 🤖 AI 예문 자동 생성 
    # ==============================================
    if st.button("📖 예문 보기/가리기", key=f"e_{mode_name}"): 
        st.session_state.show_example = not st.session_state.show_example
        
        if st.session_state.show_example:
            if pd.isna(row['예문']) or str(row['예문']).strip() == "" or str(row['예문']).strip() == "nan":
                if HAS_GENAI and MY_GEMINI_API_KEY and MY_GEMINI_API_KEY != "여기에_아버님의_API키를_붙여넣으세요":
                    with st.spinner("🤖 AI 비서가 예문을 영작 중입니다..."):
                        try:
                            genai.configure(api_key=MY_GEMINI_API_KEY)
                            
                            valid_models = []
                            for m in genai.list_models():
                                if 'generateContent' in m.supported_generation_methods:
                                    valid_models.append(m.name)
                            
                            if not valid_models:
                                st.error("이 API 키로 사용할 수 있는 텍스트 생성 모델이 없습니다.")
                            else:
                                target_model = valid_models[0]
                                for v in valid_models:
                                    if 'flash' in v: target_model = v; break
                                    elif 'pro' in v: target_model = v

                                model = genai.GenerativeModel(target_model)
                                prompt = f"영단어 '{row['영어']}'(뜻: {row['한글']})가 포함된 중학생 1학년 수준의 아주 쉽고 짧은 영어 예문 1개와 한글 뜻을 만들어줘. 반드시 'I have an apple. (나는 사과를 가지고 있다.)' 처럼 딱 1줄로 대답해."
                                res = model.generate_content(prompt)
                                
                                df_idx = df[df['영어'] == row['영어']].index[0]
                                df.at[df_idx, '예문'] = res.text.strip()
                                st.session_state.main_df = df
                                conn.update(data=df)
                                st.rerun() 
                        except Exception as e:
                            st.error(f"AI 예문 생성 실패! 에러: {e}")
                else:
                    pass

    if st.session_state.show_meaning: st.success(f"정답: {row['한글']}")
    if st.session_state.show_example:
        ex_text = row['예문'] if pd.notna(row['예문']) and str(row['예문']).strip() != "" and str(row['예문']).strip() != "nan" else "등록된 예문이 없습니다. (코드 상단에 API 키가 잘 입력되었는지 확인해주세요!)"
        st.info(f"📝 예문: {ex_text}")
        
    if not st.session_state.show_meaning and not st.session_state.show_example: st.write("<div style='height: 58px;'></div>", unsafe_allow_html=True)
    if st.button("➡️ 다음 단어로", key=f"n_{mode_name}"):
        st.session_state.show_meaning = False; st.session_state.show_example = False; st.session_state.f_idx += 1; st.rerun()

with tab1: run_flashcard(level_df[(level_df['상태'] < 4) & (level_df['학교학원'] != "O")].reset_index(drop=True), "일반 단어", study_limit)
with tab2: run_flashcard(level_df[(level_df['상태'] < 4) & (level_df['학교학원'] == "O")].reset_index(drop=True), "학교/학원", study_limit)

# --- 탭 3: 실전 퀴즈 ---
with tab3:
    if not st.session_state.test_active:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✍️ 일반 시험 시작"):
                st.session_state.test_active = True; quiz_targets = level_df[(level_df['상태'] < 4) & (level_df['학교학원'] != "O")].head(study_limit)
                st.session_state.quiz_pool = quiz_targets.to_dict('records'); random.shuffle(st.session_state.quiz_pool)
                st.session_state.quiz_stats = {'total': len(quiz_targets), 'correct': 0, 'is_school_quiz': False}; st.session_state.q_done = False; st.rerun()
        with c2:
            if st.button("🏫 학교/학원 시험 시작"):
                st.session_state.test_active = True; quiz_targets = level_df[(level_df['상태'] < 4) & (level_df['학교학원'] == "O")].head(study_limit)
                st.session_state.quiz_pool = quiz_targets.to_dict('records'); random.shuffle(st.session_state.quiz_pool)
                st.session_state.quiz_stats = {'total': len(quiz_targets), 'correct': 0, 'is_school_quiz': True}; st.session_state.q_done = False; st.rerun()
    
    if st.session_state.test_active:
        if st.session_state.quiz_pool:
            q = st.session_state.quiz_pool[0]; current_q_num = st.session_state.quiz_stats['total'] - len(st.session_state.quiz_pool) + 1
            st.markdown(f"<div class='flashcard'><h3>Q{current_q_num}. 뜻은?</h3><h1 style='font-size:60px;'>{q['영어']}</h1></div>", unsafe_allow_html=True)
            
            if not st.session_state.q_done:
                ans = st.text_input("정답 입력").strip()
                if st.button("정답 확인 🚀"):
                    st.session_state.q_done = True
                    correct_list = [c.strip() for c in str(q['한글']).replace('/', ',').split(',')]
                    df_idx = df[df['영어'] == q['영어']].index[0]
                    if ans in correct_list:
                        st.session_state.q_res = True; st.session_state.quiz_stats['correct'] += 1
                        df.at[df_idx, '상태'] = int(df.at[df_idx, '상태']) + 1; df.at[df_idx, '최근학습일'] = today_str
                    else: 
                        st.session_state.q_res = False; df.at[df_idx, '상태'] = 0; df.at[df_idx, '등록일'] = today_str
                    st.session_state.main_df = df; conn.update(data=df); st.rerun()
            else:
                if st.session_state.q_res: st.balloons(); st.success(f"🎉 정답이야! ({q['한글']})")
                else: st.error(f"오답! 정답은 '{q['한글']}' (이)야.")
                if st.button("➡️ 다음 문제"): st.session_state.quiz_pool.pop(0); st.session_state.q_done = False; st.rerun()
            st.write("---")
            if st.button("🏁 강제 종료"): st.session_state.test_active = False; st.session_state.quiz_pool = []; st.rerun()
        else:
            total = st.session_state.quiz_stats['total']; correct = st.session_state.quiz_stats['correct']
            score = int((correct / total * 100)) if total > 0 else 0
            st.markdown(f"<div class='flashcard'><h2>🏁 시험 종료!</h2><h1>{score} 점</h1></div>", unsafe_allow_html=True)
            
            if is_last_day and not st.session_state.quiz_stats['is_school_quiz']:
                if score >= 90:
                    st.success("🎉 [월말 평가] 90점 돌파!!"); st.info("🎁 룰렛 티켓 1장 획득!")
                    if 'reward_given' not in st.session_state: st.session_state.spin_tickets += 1; st.session_state.reward_given = True
                elif score >= 80: st.success("🎉 진급을 축하합니다!")
                else: st.error("🚨 80점 미만! 다음 달 진급을 위해 복습하세요!")
            else:
                if score < 80 and not st.session_state.quiz_stats['is_school_quiz']:
                    st.error("🚨 80점 미만이므로 복습해야 합니다!")
                    if st.button("😭 알겠습니다"): st.session_state.force_review = True; st.session_state.test_active = False; st.session_state.f_idx = 0; st.rerun()
                elif score >= 80: st.success("🎉 통과!")
            if st.button("🏠 메인으로"):
                st.session_state.test_active = False
                if 'reward_given' in st.session_state: del st.session_state.reward_given
                st.rerun()

# --- 탭 4, 5: 룰렛, 추가 ---
with tab4:
    st.header("🎁 고은이의 선물 룰렛"); st.write(f"🎟️ **보유 티켓:** {st.session_state.spin_tickets}장")
    if st.session_state.spin_tickets > 0:
        if st.button("🎯 룰렛 돌리기", type="primary"):
            st.session_state.spin_tickets -= 1
            spin_placeholder = st.empty()
            for i in range(20): spin_placeholder.markdown(f"<div class='roulette-box'><h2>두구두구...</h2><h1>🎰 {random.choice(st.session_state.prizes)}</h1></div>", unsafe_allow_html=True); time.sleep(0.1)
            spin_placeholder.markdown(f"<div class='roulette-box'><h2 style='color:#FF4500;'>🎉 당첨!! 🎉</h2><h1>🎁 {random.choice(st.session_state.prizes)}</h1></div>", unsafe_allow_html=True); st.balloons()
    else: st.info("💡 룰렛 티켓이 없습니다. 월말 평가 90점 이상 달성 시 획득!")

with tab5:
    st.header("➕ 단어 추가")
    with st.form("new_add", clear_on_submit=True):
        eng = st.text_input("영어 단어 (필수)"); kor = st.text_input("한글 뜻 (필수)"); ex_sentence = st.text_area("예문"); lv = st.radio("레벨", ["중등", "고등"], horizontal=True)
        is_school = st.checkbox("🏫 학교/학원 단어장용")
        if st.form_submit_button("저장하기 💾"):
            if eng and kor:
                new_row = pd.DataFrame([{"영어": eng, "한글": kor, "상태": 0, "학교학원": "O" if is_school else "X", "레벨": lv, "등록일": today_str, "최근학습일": "", "예문": ex_sentence}])
                st.session_state.main_df = pd.concat([df, new_row], ignore_index=True); conn.update(data=st.session_state.main_df); st.success("저장 완료!"); time.sleep(1); st.rerun()

# --- 탭 6: 비밀의 방 ---
with tab6:
    if st.text_input("아빠 비밀번호", type="password") == "love317619":
        st.subheader("🔒 아빠의 관리소")
        m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs(["📅 캘린더", "🧹 삭제", "🎟️ 치트키", "🎁 선물"])
        
        with m_tab1:
            studied_dates = set(df['최근학습일'].dropna().replace("", pd.NA).dropna().tolist())
            cal = calendar.Calendar(firstweekday=6); month_days = cal.monthdatescalendar(datetime.now().year, datetime.now().month)
            cal_html = "<table style='width:100%; text-align:center; border-collapse:collapse;'><tr style='background:#9370DB; color:white;'><th>일</th><th>월</th><th>화</th><th>수</th><th>목</th><th>금</th><th>토</th></tr>"
            for week in month_days:
                cal_html += "<tr>"
                for d in week:
                    d_str = d.strftime('%Y-%m-%d')
                    if d.month == datetime.now().month:
                        if d_str in studied_dates: cal_html += f"<td style='padding:15px; border:1px solid #FFB6C1; background:#FFF0F5;'>🟢<br><b>{d.day}</b></td>"
                        else: cal_html += f"<td style='padding:15px; border:1px solid #ddd;'>{d.day}</td>"
                    else: cal_html += "<td style='padding:15px; border:1px solid #ddd; color:#ccc;'></td>"
                cal_html += "</tr>"
            cal_html += "</table>"; st.markdown(cal_html, unsafe_allow_html=True)
            
        with m_tab2:
            st.write("#### ⚡ 카테고리별 삭제")
            c_a, c_b = st.columns(2)
            if c_a.button("🏫 학교단어 전체 삭제"): st.session_state.main_df = df[df['학교학원'] != "O"]; conn.update(data=st.session_state.main_df); st.rerun()
            if c_b.button("👑 마스터 단어 삭제"): st.session_state.main_df = df[df['상태'] < 4]; conn.update(data=st.session_state.main_df); st.rerun()
            df_for_edit = df.copy(); df_for_edit.insert(0, "삭제선택", False)
            edited_df = st.data_editor(df_for_edit, hide_index=True, use_container_width=True, column_config={"삭제선택": st.column_config.CheckboxColumn("삭제✅", default=False)})
            if st.button("🗑️ 체크 단어 일괄 삭제"):
                words_to_del = edited_df[edited_df["삭제선택"] == True]["영어"].tolist()
                if words_to_del: st.session_state.main_df = df[~df["영어"].isin(words_to_del)]; conn.update(data=st.session_state.main_df); st.rerun()
        
        with m_tab3:
            if st.button("🎟️ 고은이에게 티켓 1장 몰래 주기"): st.session_state.spin_tickets += 1; st.success("지급 완료!"); time.sleep(1); st.rerun()
                
        with m_tab4:
            with st.form("prize_form"):
                new_prizes = [st.text_input(f"선물 {i+1}번", value=st.session_state.prizes[i]) for i in range(10)]
                if st.form_submit_button("선물 업데이트! 💾"): st.session_state.prizes = new_prizes; st.success("장전 완료!"); time.sleep(1); st.rerun()
