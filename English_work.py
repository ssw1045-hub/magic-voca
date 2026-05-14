import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time
from gtts import gTTS
import io
from datetime import datetime
import calendar

# ==========================================
# 1. UI 설정 및 상태 관리 초기화
# ==========================================
st.set_page_config(page_title="고은이의 마법 단어장", layout="centered")
st.markdown("""
<style>
    .stApp { background-color: #FFF0F5 !important; }
    h1, h2, h3, p, span, div, label, li, td, th { color: #4B0082 !important; font-family: 'Apple SD Gothic Neo', sans-serif !important; font-weight: bold !important; }
    .stButton>button { width: 100%; border-radius: 15px; background: linear-gradient(135deg, #9370DB, #8A2BE2) !important; color: white !important; font-weight: bold; height: 3.5em; box-shadow: 0px 4px 6px rgba(0,0,0,0.2); }
    .flashcard { background: white; padding: 50px 20px; border-radius: 30px; border: 4px solid #FFB6C1; text-align: center; margin-bottom: 25px; box-shadow: 0px 10px 20px rgba(255,182,193,0.4); }
    .stProgress > div > div > div > div { background-color: #9370DB !important; }
</style>
""", unsafe_allow_html=True)

st.title("💖 고은이의 마법 단어장 V14")

# 상태 변수 초기화
if 'test_active' not in st.session_state: st.session_state.test_active = False
if 'show_meaning' not in st.session_state: st.session_state.show_meaning = False
if 'flash_cycle_done' not in st.session_state: st.session_state.flash_cycle_done = False
if 'f_idx' not in st.session_state: st.session_state.f_idx = 0

# ==========================================
# 2. 구글 시트 연결 및 데이터 준비
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
try:
    df = conn.read(ttl=0)
    # 필수 컬럼: 레벨 추가
    required_cols = ['영어', '한글', '상태', '학교학원', '레벨', '등록일', '최근학습일']
    for col in required_cols:
        if col not in df.columns: df[col] = ""
        
    df['상태'] = pd.to_numeric(df['상태'], errors='coerce').fillna(0).astype(int)
    today_str = datetime.today().strftime('%Y-%m-%d')
    df['등록일'] = df['등록일'].fillna(today_str).replace("", today_str)
    # 레벨이 비어있으면 기본값 '중등'
    df['레벨'] = df['레벨'].fillna('중등').replace("", '중등')
except:
    st.error("🚨 시트 연결 실패! 설정을 확인해주세요.")
    st.stop()

# ==========================================
# 3. 레벨 선택 및 진도율 계산
# ==========================================
selected_level = st.sidebar.selectbox("🎯 학습 레벨 선택", ["중등", "고등"])
level_df = df[df['레벨'] == selected_level]

# 진도율 계산
total_cnt = len(level_df)
master_cnt = len(level_df[level_df['상태'] >= 4])
progress = (master_cnt / total_cnt) if total_cnt > 0 else 0

st.sidebar.write(f"### {selected_level} 마스터 진도")
st.sidebar.progress(progress)
st.sidebar.write(f"{master_cnt} / {total_cnt} 완료")

if progress == 1 and total_cnt > 0:
    st.sidebar.success(f"🎊 {selected_level} 완전 정복! 다음 레벨로 가세요!")

# ==========================================
# 4. 4대 핵심 탭 구성
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["👀 깜빡이 학습", "🎯 실전 퀴즈", "➕ 학교/학원 추가", "🔒 비밀의 방"])

# --- 탭 1: 깜빡이 학습 (레벨 필터링 적용) ---
with tab1:
    if st.session_state.test_active:
        st.warning("⚠️ 지금은 시험 중! 시험 탭(🎯)에서 퀴즈를 모두 마치거나 종료해야 단어를 볼 수 있어요.")
    else:
        # 선택한 레벨 중 아직 못 외운 단어들
        unmastered = level_df[level_df['상태'] < 4].reset_index(drop=True)
        
        if not unmastered.empty:
            if st.session_state.flash_cycle_done:
                st.markdown(f"<div class='flashcard'><h2>🎉 {selected_level} 1회독 완료!</h2><p>오늘의 단어를 모두 한 번씩 봤어요.</p></div>", unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 다시 복습하기"):
                        st.session_state.flash_cycle_done = False
                        st.session_state.f_idx = 0
                        st.rerun()
                with col2:
                    if st.button("✍️ 실전 퀴즈 시작"):
                        st.session_state.test_active = True
                        st.session_state.flash_cycle_done = False
                        st.rerun()
            else:
                row = unmastered.iloc[st.session_state.f_idx % len(unmastered)]
                reg_date = datetime.strptime(str(row['등록일']), '%Y-%m-%d')
                is_recent = (datetime.today() - reg_date).days <= 7
                badge = "🔥 집중 학습!" if (row['학교학원'] == "O" and is_recent) else "✨ 열공 중"
                
                st.markdown(f"<div class='flashcard'><p style='color:red;'>{badge} [{selected_level}] ( {st.session_state.f_idx + 1} / {len(unmastered)} )</p><h1 style='font-size:70px;'>{row['영어']}</h1></div>", unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🔊 발음 듣기"):
                        tts = gTTS(text=str(row['영어']), lang='en')
                        fp = io.BytesIO(); tts.write_to_fp(fp); st.audio(fp, format='audio/mp3')
                with c2:
                    if st.button("💡 뜻 보기 / 가리기"):
                        st.session_state.show_meaning = not st.session_state.show_meaning
                
                if st.session_state.show_meaning:
                    st.success(f"정답: {row['한글']}")
                else: st.write("<div style='height: 58px;'></div>", unsafe_allow_html=True)
                
                if st.button("➡️ 다음 단어로"):
                    st.session_state.show_meaning = False
                    if st.session_state.f_idx >= len(unmastered) - 1: st.session_state.flash_cycle_done = True
                    else: st.session_state.f_idx += 1
                    st.rerun()
        else:
            st.success(f"🎊 {selected_level} 단어를 모두 마스터했거나 단어가 없어요!")

# --- 탭 2: 실전 퀴즈 (레벨 필터링 적용) ---
with tab2:
    if not st.session_state.test_active:
        if st.button("✍️ 시험 시작하기"):
            st.session_state.test_active = True
            st.rerun()
    
    if st.session_state.test_active:
        targets = level_df[level_df['상태'] < 4]
        if not targets.empty:
            if 'q_word' not in st.session_state:
                st.session_state.q_word = targets.sample(1).iloc[0]
                st.session_state.q_done = False

            q = st.session_state.q_word
            st.markdown(f"<div class='flashcard'><h3>[{selected_level} 퀴즈]</h3><h1 style='font-size:60px;'>{q['영어']}</h1></div>", unsafe_allow_html=True)
            
            if not st.session_state.q_done:
                ans = st.text_input("정답 입력", key=f"q_{q['영어']}").strip()
                if st.button("정답 확인 🚀"):
                    st.session_state.q_done = True
                    if ans == str(q['한글']).strip():
                        st.session_state.q_res = True
                        df_idx = df[df['영어'] == q['영어']].index[0]
                        df.at[df_idx, '상태'] += 1
                        df.at[df_idx, '최근학습일'] = today_str
                        conn.update(data=df)
                    else: st.session_state.q_res = False
                    st.rerun()
            else:
                if st.session_state.q_res: st.balloons(); st.success(f"정답: {q['한글']}")
                else: st.error(f"오답! 정답은 '{q['한글']}'")
                if st.button("➡️ 다음 문제"):
                    del st.session_state.q_word
                    st.rerun()
            
            if st.button("🏁 시험 종료"):
                st.session_state.test_active = False
                st.rerun()
        else:
            st.success(f"🎉 {selected_level} 시험을 모두 마쳤습니다!")
            st.session_state.test_active = False

# --- 탭 3: 학교 및 학원 단어장 (레벨 선택 추가) ---
with tab3:
    st.header("🏫 학교 및 학원 단어 추가")
    with st.form("level_add", clear_on_submit=True):
        eng = st.text_input("영어 단어")
        kor = st.text_input("한글 뜻")
        lv = st.radio("단어 레벨", ["중등", "고등"], horizontal=True)
        if st.form_submit_button("단어장에 저장하기 💾"):
            if eng and kor:
                new_row = pd.DataFrame([{"영어": eng, "한글": kor, "상태": 0, "학교학원": "O", "레벨": lv, "등록일": today_str, "최근학습일": ""}])
                conn.update(data=pd.concat([df, new_row], ignore_index=True))
                st.success(f"{lv} 단어장에 저장되었습니다!")
                time.sleep(1); st.rerun()

# --- 탭 4: 비밀의 방 (캘린더 + 레벨별 관리) ---
with tab4:
    if st.text_input("아빠 비밀번호", type="password") == "love317619":
        st.subheader("🔒 아빠의 관리소")
        m_tab1, m_tab2, m_tab3 = st.tabs(["📅 미션 캘린더", "📊 전체 현황", "💣 데이터 정리"])
        
        with m_tab1:
            st.write("### 📅 학습 완료 기록")
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
            st.write(f"현재 총 {len(df)}개의 단어가 저장되어 있습니다.")
            st.dataframe(df[['영어', '한글', '레벨', '상태', '등록일']])
            
        with m_tab3:
            if st.button("💣 전체 데이터 초기화"):
                conn.update(data=pd.DataFrame(columns=required_cols))
                st.success("초기화 완료!"); st.rerun()
            st.write("---")
            target_w = st.selectbox("초기화할 단어", df['영어'].tolist())
            if st.button("🔄 상태 초기화"):
                df.loc[df['영어'] == target_w, '상태'] = 0
                conn.update(data=df); st.success("초기화!"); st.rerun()
