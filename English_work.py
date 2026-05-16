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
# 🎁 아빠의 룰렛 선물 10가지 기본 설정 (영구 저장용)
# 여기서 선물을 수정해두시면 앱이 꺼졌다 켜져도 유지됩니다!
# ==========================================
default_prizes = [
    "💸 용돈 3,000원", 
    "🍦 베스킨라빈스 싱글", 
    "🍗 아빠가 쏘는 치킨!",
    "🎮 게임 1시간 이용권", 
    "🎬 보고 싶은 영화 보기", 
    "떡볶이 사먹기 찬스",
    "마라탕 쏘기!", 
    "원하는 간식 1개 고르기", 
    "휴식권 30분", 
    "아빠의 폭풍 칭찬 및 안마"
]

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
    .roulette-box { background: #FFF8DC; padding: 40px; border-radius: 30px; border: 5px dashed #FFD700; text-align: center; margin: 20px 0; }
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
if 'spin_tickets' not in st.session_state: st.session_state.spin_tickets = 0
if 'prizes' not in st.session_state: st.session_state.prizes = default_prizes # 커스텀 선물 10종 로드

# ==========================================
# 2. 구글 시트 고속 메모리 연동
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
required_cols = ['영어', '한글', '상태', '학교학원', '레벨', '등록일', '최근학습일', '예문']

if 'main_df' not in st.session_state:
    try:
        loaded_df = conn.read(ttl=0)
        for col in required_cols:
            if col not in loaded_df.columns: loaded_df[col] = ""
            
        loaded_df['상태'] = pd.to_numeric(loaded_df['상태'], errors='coerce').fillna(0).astype(int)
        today_str = datetime.today().strftime('%Y-%m-%d')
        loaded_df['등록일'] = loaded_df['등록일'].fillna(today_str).replace("", today_str)
        loaded_df['레벨'] = loaded_df['레벨'].fillna('중등').replace("", '중등')
        st.session_state.main_df = loaded_df
    except Exception as e:
        st.error(f"🚨 구글 시트 연결 실패! (원인: {e})")
        st.stop()

df = st.session_state.main_df

# ==========================================
# 3. 달력 인지 (일요일 시작 알고리즘 + 월말 총평가)
# ==========================================
today_date = datetime.today()
today_str = today_date.strftime('%Y-%m-%d')

# 파이썬 기본: 0=월, 1=화, ... 5=토, 6=일
# 아빠의 규칙: 일=0, 월=1, ... 토=6 으로 변환
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
    st.sidebar.error(f"🔥 오늘은 {today_date.month}월의 마지막 날!\n대망의 [월말 총평가] 날입니다. 90점 이상 받고 룰렛 티켓을 노려보세요!")
elif custom_weekday == 6: # 6 = 토요일 (총복습일)
    study_limit = 180
    st.sidebar.success(f"👑 오늘은 {today_name}!\n신규 진도 없이 이번 주 배운 단어 총복습 및 시험일입니다.")
else: # 0~5 = 일요일~금요일 (진도 나가는 날)
    study_limit = (custom_weekday + 1) * 30
    st.sidebar.info(f"📅 오늘은 {today_name}!\n누적 {study_limit}개 단어 학습일입니다.")

st.sidebar.write("---")
st.sidebar.write(f"### {selected_level} 마스터 진도")
st.sidebar.progress(progress)
st.sidebar.write(f"{master_cnt} / {total_cnt} 완료")

st.sidebar.write("---")
if st.sidebar.button("🔄 구글시트 강제 동기화"):
    if 'main_df' in st.session_state: del st.session_state.main_df
    st.rerun()

# ==========================================
# 4. 6대 탭 구성
# ==========================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["👀 일반", "🏫 학교", "🎯 퀴즈", "🎁 룰렛", "➕ 추가", "🔒 비밀"])

# --- 공통 함수: 깜빡이 학습 ---
def run_flashcard(target_list, mode_name, limit):
    if st.session_state.test_active:
        st.warning(f"⚠️ 시험 중에는 단어를 볼 수 없어요!")
        return

    if st.session_state.force_review and mode_name == "일반 단어":
        st.error("🚨 이전 시험에서 80점 미만을 받았어요! 다시 철저하게 복습하세요! 🚨")

    target_list = target_list.head(limit)

    if target_list.empty:
        st.success(f"🎊 {mode_name}에 공부할 단어가 없어요!")
        return

    if st.session_state.f_idx >= len(target_list):
        st.session_state.force_review = False
        msg_title = "월말 총복습 완료!" if is_last_day else f"{mode_name} {len(target_list)}개 학습 완료!"
        st.markdown(f"<div class='flashcard'><h2>🎉 {msg_title}</h2><p>목표량을 다 채웠어요! 이제 무엇을 할까요?</p></div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 처음부터 복습하기", key=f"replay_{mode_name}"):
                st.session_state.f_idx = 0; st.rerun()
        with col2:
            if st.button("✍️ 실전 퀴즈로 가기", key=f"go_quiz_{mode_name}"):
                st.session_state.test_active = True; st.session_state.f_idx = 0; st.rerun()
        return

    row = target_list.iloc[st.session_state.f_idx]
    reg_date = datetime.strptime(str(row['등록일']), '%Y-%m-%d')
    is_recent = (datetime.today() - reg_date).days <= 7
    badge = "🔥 집중 복습!" if is_recent else "✨ 학습 중"
    
    st.markdown(f"<div class='flashcard'><p style='color:red;'>{badge} [{mode_name}] ( {st.session_state.f_idx + 1} / {len(target_list)} )</p><h1 style='font-size:70px;'>{row['영어']}</h1></div>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔊 발음 듣기", key=f"audio_{mode_name}"):
            tts = gTTS(text=str(row['영어']), lang='en'); fp = io.BytesIO(); tts.write_to_fp(fp); st.audio(fp, format='audio/mp3')
    with c2:
        if st.button("💡 뜻 보기/가리기", key=f"toggle_{mode_name}"):
            st.session_state.show_meaning = not st.session_state.show_meaning

    if st.button("📖 예문 보기/가리기", key=f"ex_btn_{mode_name}"): st.session_state.show_example = not st.session_state.show_example
    
    if st.session_state.show_meaning: st.success(f"정답: {row['한글']}")
    if st.session_state.show_example:
        ex_text = row['예문'] if pd.notna(row['예문']) and str(row['예문']).strip() != "" else "등록된 예문이 없습니다."
        st.info(f"📝 예문: {ex_text}")
    if not st.session_state.show_meaning and not st.session_state.show_example: st.write("<div style='height: 58px;'></div>", unsafe_allow_html=True)
    
    if st.button("➡️ 다음 단어로", key=f"next_{mode_name}"):
        st.session_state.show_meaning = False; st.session_state.show_example = False; st.session_state.f_idx += 1; st.rerun()

# --- 탭 1, 2: 깜빡이 ---
with tab1: run_flashcard(level_df[(level_df['상태'] < 4) & (level_df['학교학원'] != "O")].reset_index(drop=True), "일반 단어", study_limit)
with tab2: run_flashcard(level_df[(level_df['상태'] < 4) & (level_df['학교학원'] == "O")].reset_index(drop=True), "학교/학원", study_limit)

# --- 탭 3: 실전 퀴즈 ---
with tab3:
    if not st.session_state.test_active:
        st.write("### 어떤 시험을 볼까요?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✍️ 일반 시험 시작"):
                st.session_state.test_active = True
                quiz_targets = level_df[(level_df['상태'] < 4) & (level_df['학교학원'] != "O")].head(study_limit)
                st.session_state.quiz_pool = quiz_targets.to_dict('records'); random.shuffle(st.session_state.quiz_pool)
                st.session_state.quiz_stats = {'total': len(quiz_targets), 'correct': 0, 'is_school_quiz': False}; st.session_state.q_done = False; st.rerun()
        with c2:
            if st.button("🏫 학교/학원 시험 시작"):
                st.session_state.test_active = True
                quiz_targets = level_df[(level_df['상태'] < 4) & (level_df['학교학원'] == "O")].head(study_limit)
                st.session_state.quiz_pool = quiz_targets.to_dict('records'); random.shuffle(st.session_state.quiz_pool)
                st.session_state.quiz_stats = {'total': len(quiz_targets), 'correct': 0, 'is_school_quiz': True}; st.session_state.q_done = False; st.rerun()
    
    if st.session_state.test_active:
        if st.session_state.quiz_pool:
            q = st.session_state.quiz_pool[0]
            current_q_num = st.session_state.quiz_stats['total'] - len(st.session_state.quiz_pool) + 1
            st.markdown(f"<div class='flashcard'><h3>Q{current_q_num}. 뜻을 맞혀보세요!</h3><h1 style='font-size:60px;'>{q['영어']}</h1></div>", unsafe_allow_html=True)
            
            if not st.session_state.q_done:
                ans = st.text_input("정답 입력", key=f"q_{q['영어']}").strip()
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
            if st.button("🏁 시험 강제 종료"): st.session_state.test_active = False; st.session_state.quiz_pool = []; st.rerun()
                
        else:
            total = st.session_state.quiz_stats['total']
            correct = st.session_state.quiz_stats['correct']
            score = int((correct / total * 100)) if total > 0 else 0
            
            st.markdown(f"<div class='flashcard'><h2>🏁 시험 종료!</h2><h1>{score} 점</h1><p>{total}문제 중 {correct}문제 정답</p></div>", unsafe_allow_html=True)
            
            # 월말 평가 보상 시스템
            if is_last_day and not st.session_state.quiz_stats['is_school_quiz']:
                if score >= 90:
                    st.success("🎉 [월말 평가] 90점 돌파!! 엄청난 실력이네요!")
                    st.info("🎁 선물 룰렛 티켓 1장을 획득했습니다! [🎁 룰렛] 탭으로 가서 돌려보세요!")
                    if 'reward_given' not in st.session_state:
                        st.session_state.spin_tickets += 1
                        st.session_state.reward_given = True
                elif score >= 80:
                    st.success("🎉 [월말 평가] 80점 이상! 다음 차수 진급을 축하합니다!")
                else:
                    st.error("🚨 [월말 평가] 80점 미만입니다. 다음 달 진급을 위해 다시 철저하게 복습하세요!")
            else:
                if score < 80 and not st.session_state.quiz_stats['is_school_quiz']:
                    st.error("🚨 80점 미만이므로 [일반 깜빡이] 탭으로 돌아가 다시 복습해야 합니다!")
                    if st.button("😭 알겠습니다"):
                        st.session_state.force_review = True; st.session_state.test_active = False; st.session_state.f_idx = 0; st.rerun()
                elif score >= 80: st.success("🎉 80점 이상 통과! 참 잘했어요!")

            if st.button("🏠 메인으로 가기"):
                st.session_state.test_active = False
                if 'reward_given' in st.session_state: del st.session_state.reward_given
                st.rerun()

# --- 탭 4: 🎁 보상 룰렛 ---
with tab4:
    st.header("🎁 고은이의 선물 룰렛")
    st.write(f"🎟️ **현재 보유한 티켓:** {st.session_state.spin_tickets}장")
    
    # 설정된 10개의 선물 리스트 가져오기
    prizes = st.session_state.prizes 
    
    if st.session_state.spin_tickets > 0:
        if st.button("🎯 룰렛 돌리기 (티켓 1장 사용)", type="primary"):
            st.session_state.spin_tickets -= 1
            
            spin_placeholder = st.empty()
            for i in range(20):
                random_prize = random.choice(prizes)
                spin_placeholder.markdown(f"<div class='roulette-box'><h2 style='color:#bbb;'>두구두구두구...</h2><h1 style='font-size:50px;'>🎰 {random_prize}</h1></div>", unsafe_allow_html=True)
                time.sleep(0.1)
                
            final_prize = random.choice(prizes)
            spin_placeholder.markdown(f"<div class='roulette-box'><h2 style='color:#FF4500;'>🎉 축하합니다! 당첨!! 🎉</h2><h1 style='font-size:50px;'>🎁 {final_prize}</h1><p>아빠한테 화면을 보여주고 선물을 받으세요!</p></div>", unsafe_allow_html=True)
            st.balloons()
    else:
        st.info("💡 룰렛 티켓이 없습니다. 매월 마지막 날 '월말 평가'에서 90점 이상을 받으면 티켓을 얻을 수 있어요!")

# --- 탭 5: 단어 추가 ---
with tab5:
    st.header("➕ 단어 추가 (SGE)")
    with st.form("new_add", clear_on_submit=True):
        eng = st.text_input("영어 단어 (필수)"); kor = st.text_input("한글 뜻 (필수)"); ex_sentence = st.text_area("예문"); lv = st.radio("레벨", ["중등", "고등"], horizontal=True)
        is_school = st.checkbox("🏫 학교/학원 단어장용")
        if st.form_submit_button("저장하기 💾"):
            if eng and kor:
                new_row = pd.DataFrame([{"영어": eng, "한글": kor, "상태": 0, "학교학원": "O" if is_school else "X", "레벨": lv, "등록일": today_str, "최근학습일": "", "예문": ex_sentence}])
                st.session_state.main_df = pd.concat([df, new_row], ignore_index=True); conn.update(data=st.session_state.main_df); st.success("저장 완료!"); time.sleep(1); st.rerun()

# --- 탭 6: 비밀의 방 (선물 설정 추가!) ---
with tab6:
    if st.text_input("아빠 비밀번호", type="password") == "love317619":
        st.subheader("🔒 아빠의 관리소")
        m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs(["📅 학습 캘린더", "🧹 데이터 관리", "🎟️ 치트키(테스트)", "🎁 선물 설정"])
        
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
            if not df.empty:
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("🏫 학교단어 전체 삭제"): st.session_state.main_df = df[df['학교학원'] != "O"]; conn.update(data=st.session_state.main_df); st.rerun()
                with col_b:
                    if st.button("👑 마스터 단어 삭제"): st.session_state.main_df = df[df['상태'] < 4]; conn.update(data=st.session_state.main_df); st.rerun()
                
                df_for_edit = df.copy(); df_for_edit.insert(0, "삭제선택", False)
                edited_df = st.data_editor(df_for_edit, hide_index=True, use_container_width=True, column_config={"삭제선택": st.column_config.CheckboxColumn("삭제✅", default=False)})
                if st.button("🗑️ 체크 단어 일괄 삭제"):
                    words_to_del = edited_df[edited_df["삭제선택"] == True]["영어"].tolist()
                    if words_to_del: st.session_state.main_df = df[~df["영어"].isin(words_to_del)]; conn.update(data=st.session_state.main_df); st.rerun()
        
        with m_tab3:
            st.write("### 🛠️ 시스템 테스트 및 보상 지급")
            st.write(f"현재 고은이의 룰렛 티켓: **{st.session_state.spin_tickets}장**")
            if st.button("🎟️ 고은이에게 티켓 1장 몰래 주기 (룰렛 테스트용)"):
                st.session_state.spin_tickets += 1
                st.success("티켓 1장이 지급되었습니다! [🎁 룰렛] 탭에서 확인해 보세요."); time.sleep(1); st.rerun()
                
        # 🎁 대망의 10가지 룰렛 선물 직접 설정!
        with m_tab4:
            st.write("### 🎁 룰렛 당첨 선물 10개 커스텀 설정")
            st.info("💡 이곳에서 입력 후 저장하시면 이번에 앱을 켜두는 동안 반영됩니다. 영구적으로 바꾸시려면 파이썬 코드 상단의 `default_prizes` 부분(13번째 줄)을 직접 수정해주세요!")
            with st.form("prize_form"):
                new_prizes = []
                for i in range(10):
                    new_val = st.text_input(f"선물 {i+1}번", value=st.session_state.prizes[i])
                    new_prizes.append(new_val)
                if st.form_submit_button("선물 10개 목록 업데이트! 💾"):
                    st.session_state.prizes = new_prizes
                    st.success("새로운 선물이 룰렛에 장전되었습니다!")
                    time.sleep(1); st.rerun()
