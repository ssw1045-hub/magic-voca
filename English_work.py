import streamlit as st
import random
import time
import pandas as pd
from datetime import datetime, timedelta
from gtts import gTTS
import io

# ==========================================
# 1. 웹페이지 기본 설정 & 감성 UI
# ==========================================
st.set_page_config(page_title="마법의 영단어장", page_icon="🦄", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #FFF0F5; }
    h1, h2, h3 { color: #9370DB; font-family: 'Comic Sans MS', 'Malgun Gothic', sans-serif; }
    .stProgress > div > div > div > div { background-color: #FF69B4; }
    .stButton>button { border-radius: 20px; border: 2px solid #FFB6C1; font-weight: bold; transition: 0.3s; }
    .stButton>button:hover { background-color: #FFB6C1; color: white; }
    .quiz-box { background-color: #FFE4E1; padding: 20px; border-radius: 15px; border: 2px dashed #FF69B4; text-align: center; margin-bottom: 10px; }
    .level-badge { background-color: #FF1493; color: white; padding: 5px 10px; border-radius: 10px; font-size: 14px; }
    .urgent-badge { background-color: #DC143C; color: white; padding: 5px 10px; border-radius: 10px; font-size: 14px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 데이터 초기화 (완전 백지 상태) & 스케줄 엔진
# ==========================================
# 샘플 데이터 모두 삭제! 이제 CSV나 수동 입력으로만 단어가 추가됩니다.
if 'vocab' not in st.session_state:
    st.session_state.vocab = {}

if 'daily_goal' not in st.session_state:
    st.session_state.daily_goal = 50 
if 'daddy_letter' not in st.session_state:
    st.session_state.daddy_letter = "우리 예쁜 딸! 오늘도 열심히 해줘서 고마워. 아빠가 사랑해! 💕"

# 하위 버전 호환: mastered_date가 없는 데이터 방어 로직
for d in st.session_state.vocab.values():
    if "mastered_date" not in d:
        d["mastered_date"] = None

today_obj = datetime.now()
today_str = today_obj.strftime("%Y-%m-%d")
is_sunday = today_obj.weekday() == 6

# 스케줄 엔진 초기화
if 'last_assign_date' not in st.session_state:
    assigned_dates = [d["assigned_date"] for d in st.session_state.vocab.values() if d["assigned_date"] is not None]
    st.session_state.last_assign_date = max(assigned_dates) if assigned_dates else (today_obj - timedelta(days=1)).strftime("%Y-%m-%d")

# --- 핵심 로직: 5/16 이후 '내일' 치 단어 당겨오기 ---
if today_str >= "2026-05-16":
    target_assign_date_str = (today_obj + timedelta(days=1)).strftime("%Y-%m-%d") 
else:
    target_assign_date_str = today_str 

# 진도 배정 엔진 (주의: 'is_urgent' 집중 오답 단어는 하루 진도 할당량에서 제외됩니다!)
while st.session_state.last_assign_date < target_assign_date_str:
    next_date_obj = datetime.strptime(st.session_state.last_assign_date, "%Y-%m-%d") + timedelta(days=1)
    next_date_str = next_date_obj.strftime("%Y-%m-%d")
    
    new_assign_count = 0
    for level in ["중학", "고등"]:
        for eng, data in st.session_state.vocab.items():
            if new_assign_count >= st.session_state.daily_goal: break
            # 일반 단어만 진도로 할당 (집중 오답 단어는 별도 관리)
            if data["assigned_date"] is None and data["level"] == level and not data.get("is_urgent"):
                st.session_state.vocab[eng]["assigned_date"] = next_date_str
                new_assign_count += 1
                
    st.session_state.last_assign_date = next_date_str
    
    if new_assign_count > 0:
        if today_str >= "2026-05-16" and next_date_str > today_str:
            st.toast(f"🚀 패턴 적용! 내일({next_date_str}) 진도 {new_assign_count}개를 당겨왔어요!", icon="📅")
        else:
            st.toast(f"📅 {next_date_str}일자 새 단어 {new_assign_count}개가 배정되었습니다!", icon="📅")

def get_status_icon(data):
    if data.get("is_urgent") and data["status"] < 4: return "🚨"
    return {0: "🥚", 1: "🔒", 2: "🌱", 3: "🌷", 4: "👑"}.get(data["status"], "🥚")

def get_audio(word):
    try:
        tts = gTTS(text=word, lang='en', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

# 학습할 리스트 필터링 함수 (진도 vs 집중 오답)
def get_study_list(mode):
    if mode == "🚨 집중 오답 노트":
        # 오답 단어만 100% 모아서 반환
        return [k for k, v in st.session_state.vocab.items() if v.get("is_urgent") and v["status"] < 4]
    else:
        # 일반 진도 단어 반환
        lst = [k for k, v in st.session_state.vocab.items() if v["assigned_date"] is not None and v["status"] < 4 and not v.get("is_urgent")]
        if is_sunday:
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            for k, v in st.session_state.vocab.items():
                if v.get("assigned_date") and v["assigned_date"] >= week_ago and not v.get("is_urgent") and v["status"] == 4:
                    if k not in lst: lst.append(k)
        random.shuffle(lst)
        return lst

# ==========================================
# 3. 메인 화면 헤더 (게이지)
# ==========================================
st.markdown("<h1 style='text-align: center;'>🦄 마법의 영단어장 V8 ✨</h1>", unsafe_allow_html=True)

if today_str >= "2026-05-16":
    st.info("💡 **특별 학습 패턴!** 내일 치 단어를 미리 당겨왔어요. 이틀에 걸쳐 여유 있게 마스터해 보세요!")
    title_text = "🎀 오늘~내일 진도 미션"
else:
    title_text = "🎀 오늘의 진도 미션"

# 일반 단어(진도) 진행률 계산
today_targets = [k for k, v in st.session_state.vocab.items() if v.get("assigned_date") is not None and v["status"] < 4 and not v.get("is_urgent")]
mastered_today = sum(1 for d in st.session_state.vocab.values() if d.get("mastered_date") == today_str and not d.get("is_urgent"))
total_today_mission = len(today_targets) + mastered_today

progress_ratio = mastered_today / total_today_mission if total_today_mission > 0 else 1.0

st.markdown(f"### {title_text} ({mastered_today} / {total_today_mission})")
st.progress(progress_ratio)

# 집중 오답 노트 알림판
urgent_pending = sum(1 for d in st.session_state.vocab.values() if d.get("is_urgent") and d["status"] < 4)
if urgent_pending > 0:
    st.warning(f"🚨 **비상!** 직접 추가한 [집중 오답 단어]가 **{urgent_pending}개** 대기 중이에요. 탭에서 모드를 변경해 외워주세요!")

if progress_ratio >= 1.0 and total_today_mission > 0:
    st.balloons()
    st.success("🎉 오늘 목표를 완벽하게 해냈어요! 아빠의 편지가 도착했습니다 💌")
    st.info(f"💌 {st.session_state.daddy_letter}")

st.write("---")

tab1, tab2, tab3, tab4 = st.tabs(["👀 단어 학습", "🎯 마법 퀴즈", "⚙️ 단어 추가하기", "🔒 비밀의 방"])

# ==========================================
# 탭 1: 단어 학습 (모드 분리)
# ==========================================
with tab1:
    st.subheader("👀 학습 모드 선택")
    mode1 = st.radio("어떤 단어를 학습할까요?", ["🌈 오늘의 진도", "🚨 집중 오답 노트"], horizontal=True, key="mode1")
    
    # 모드가 바뀌면 카드 순서 초기화
    if 'prev_mode1' not in st.session_state or st.session_state.prev_mode1 != mode1:
        st.session_state.f_idx = 0
        st.session_state.f_show = False
        st.session_state.prev_mode1 = mode1

    study_list_1 = get_study_list(mode1)
    
    st.write("---")
    if not study_list_1:
        st.success("이 모드에 할당된 단어를 모두 마스터했어요! 👑")
    else:
        if st.session_state.f_idx < len(study_list_1):
            eng = study_list_1[st.session_state.f_idx]
            data = st.session_state.vocab[eng]
            
            badge_html = f"<span class='urgent-badge'>집중 오답</span>" if data.get("is_urgent") else f"<span class='level-badge'>{data['level']}</span>"
            st.markdown(f"**상태:** {get_status_icon(data)} | {badge_html}", unsafe_allow_html=True)
            
            if not st.session_state.f_show:
                aud = get_audio(eng)
                if aud: st.audio(aud, format="audio/mp3", autoplay=True)
                st.markdown(f"<div class='quiz-box'><h1 style='font-size:70px;'>{eng}</h1><h1 style='color:transparent;'>?</h1></div>", unsafe_allow_html=True)
                if st.button("뜻 보기 👀", use_container_width=True):
                    st.session_state.f_show = True
                    st.rerun()
            else:
                st.markdown(f"<div class='quiz-box'><h1 style='font-size:70px;'>{eng}</h1><h1 style='color:#FF69B4;'>{data['mean']}</h1></div>", unsafe_allow_html=True)
                if st.button("다음 단어 ⏭️", use_container_width=True):
                    st.session_state.f_idx += 1
                    st.session_state.f_show = False
                    st.rerun()
        else:
            if st.button("다시 학습하기 🔄"):
                st.session_state.f_idx = 0
                st.rerun()

# ==========================================
# 탭 2: 마법 퀴즈 (모드 분리)
# ==========================================
with tab2:
    st.subheader("🎯 퀴즈 모드 선택")
    mode2 = st.radio("어떤 단어로 시험을 볼까요?", ["🌈 오늘의 진도", "🚨 집중 오답 노트"], horizontal=True, key="mode2")
    
    if 'prev_mode2' not in st.session_state or st.session_state.prev_mode2 != mode2:
        st.session_state.q_word = None
        st.session_state.prev_mode2 = mode2

    study_list_2 = get_study_list(mode2)
    
    st.write("---")
    if not study_list_2:
        st.success("이 모드의 모든 단어를 마스터했습니다! 🎉")
    else:
        # 단어가 남아있는데 q_word가 비어있거나 현재 리스트에 없다면 새로 뽑기
        if not st.session_state.q_word or st.session_state.q_word not in study_list_2:
            st.session_state.q_word = random.choice(study_list_2)
        
        q_eng = st.session_state.q_word
        data = st.session_state.vocab[q_eng]
        
        badge_html = f"<span class='urgent-badge'>집중 오답</span>" if data.get("is_urgent") else f"<span class='level-badge'>{data['level']}</span>"
        st.markdown(f"<div style='text-align:center;'><h3>상태: {get_status_icon(data)} | {badge_html}</h3></div>", unsafe_allow_html=True)
        st.markdown(f"<h1 style='text-align:center; font-size:60px;'>{q_eng}</h1>", unsafe_allow_html=True)
        
        if st.button("🔊 발음 듣기", use_container_width=True):
            aud = get_audio(q_eng)
            if aud: st.audio(aud, format="audio/mp3", autoplay=True)
            
        st.markdown("<div class='quiz-box'><span style='color:#FF1493; font-weight:bold;'>✨ 이곳에 정답(한글)을 적어주세요 ✨</span></div>", unsafe_allow_html=True)
        ans = st.text_input("", placeholder="예: 사과", label_visibility="collapsed", key="q_input")
        
        if st.button("정답 제출 🚀", use_container_width=True, type="primary"):
            if ans.strip() == data["mean"]:
                st.session_state.vocab[q_eng]["streak"] += 1
                if st.session_state.vocab[q_eng]["streak"] >= 3:
                    st.session_state.vocab[q_eng]["status"] = 4
                    st.session_state.vocab[q_eng]["mastered_date"] = today_str 
                    st.balloons()
                else: 
                    st.session_state.vocab[q_eng]["status"] = st.session_state.vocab[q_eng]["streak"] + 1
                st.success("정답이야! ✨")
            else:
                st.session_state.vocab[q_eng]["streak"] = 0
                st.session_state.vocab[q_eng]["status"] = 1
                st.error(f"틀렸어 😭 정답은 '{data['mean']}'이야.")
            time.sleep(1.2)
            
            # 다음 퀴즈 단어 세팅
            new_list = get_study_list(mode2)
            if new_list:
                st.session_state.q_word = random.choice(new_list)
            else:
                st.session_state.q_word = None
            st.rerun()

# ==========================================
# 탭 3: 단어 추가하기
# ==========================================
with tab3:
    st.subheader("⚙️ 단어 추가 및 CSV 업로드")
    st.info("💡 단어 삭제는 '비밀의 방'에서 아빠만 할 수 있어요!")
    
    with st.form("add_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1: n_eng = st.text_input("영어")
        with c2: n_kor = st.text_input("한글")
        with c3: n_lvl = st.selectbox("레벨", ["중학", "고등"])
        
        st.markdown("---")
        is_u = st.checkbox("🚨 학교/문제집에서 틀린 단어 (오늘 진도량에서 제외 & 오답노트에서 별도 관리)")
        if st.form_submit_button("➕ 단어 추가"):
            if n_eng and n_kor:
                st.session_state.vocab[n_eng.lower().strip()] = {
                    "mean": n_kor.strip(), "level": n_lvl, "status": 1 if is_u else 0,
                    "streak": 0, "assigned_date": None, "is_urgent": is_u, "mastered_date": None
                }
                if is_u:
                    st.error("🚨 집중 오답 노트에 단어가 추가되었습니다!")
                else:
                    st.success("✅ 일반 단어장에 단어가 추가되었습니다!")
                st.rerun()

    st.markdown("---")
    up_file = st.file_uploader("📂 CSV 파일로 일반 단어 넣기", type=["csv"])
    if up_file and st.button("데이터 병합 🚀"):
        try:
            df = pd.read_csv(up_file, encoding='utf-8')
        except UnicodeDecodeError:
            up_file.seek(0)
            df = pd.read_csv(up_file, encoding='cp949')
        added = 0
        for _, row in df.iterrows():
            try:
                e = str(row.iloc[0]).lower().strip()
                if e and e not in st.session_state.vocab and e != "nan":
                    st.session_state.vocab[e] = {
                        "mean": str(row.iloc[1]).strip() if len(row) > 1 else "",
                        "level": str(row.iloc[2]).strip() if len(row) > 2 else "중학",
                        "status": 0, "streak": 0, "assigned_date": None, "is_urgent": False, "mastered_date": None
                    }
                    added += 1
            except: continue
        st.success(f"엑셀에서 {added}개의 단어가 성공적으로 추가되었습니다!")
        time.sleep(1)
        st.rerun()

# ==========================================
# 탭 4: 비밀의 방 (보안 강화 & 관리 기능)
# ==========================================
with tab4:
    st.subheader("🔒 아빠 전용 비밀의 방")
    pw = st.text_input("비밀번호를 입력하세요", type="password")
    
    if pw == "love317619":
        st.success("✅ 아빠 인증 완료!")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("총 단어", len(st.session_state.vocab))
        c2.metric("하루 목표 분량", st.session_state.daily_goal)
        c3.metric("마스터 👑", sum(1 for d in st.session_state.vocab.values() if d["status"] == 4))
        
        st.write("---")
        n_goal = st.number_input("하루 목표 개수 조정", value=st.session_state.daily_goal)
        if st.button("목표 저장"): st.session_state.daily_goal = n_goal
        n_let = st.text_area("아빠의 편지 수정", value=st.session_state.daddy_letter)
        if st.button("편지 저장"): st.session_state.daddy_letter = n_let
        
        st.write("---")
        st.markdown("#### 🗑️ 개별 단어 관리 (삭제)")
        search_q = st.text_input("삭제할 단어 검색")
        for eng, d in list(st.session_state.vocab.items()):
            if search_q and search_q in eng:
                col_a, col_b, col_c = st.columns([2, 2, 1])
                with col_a: st.write(f"**{eng}** ({get_status_icon(d)})")
                with col_b: st.write(d["mean"])
                with col_c:
                    if st.button("삭제", key=f"del_{eng}"):
                        del st.session_state.vocab[eng]
                        st.rerun()

        st.write("---")
        st.markdown("#### 📅 날짜별 일괄 삭제 (Daily 삭제)")
        dates = sorted(list(set(d["assigned_date"] for d in st.session_state.vocab.values() if d["assigned_date"] is not None)))
        if dates:
            target_date = st.selectbox("삭제할 배정 날짜를 선택하세요", dates)
            if st.button(f"🔥 {target_date} 단어 모두 삭제"):
                keys_to_del = [k for k, v in st.session_state.vocab.items() if v["assigned_date"] == target_date]
                for k in keys_to_del: del st.session_state.vocab[k]
                st.success(f"{len(keys_to_del)}개의 단어를 삭제했습니다.")
                st.rerun()
        else: st.write("삭제할 날짜 데이터가 없습니다.")

        st.write("---")
        st.markdown("#### 💣 전체 삭제 (초기화)")
        chk_all = st.checkbox("정말로 모든 단어를 삭제하시겠습니까? (복구 불가)")
        if chk_all and st.button("전체 단어 영구 삭제", type="primary"):
            st.session_state.vocab = {}
            st.session_state.last_assign_date = (today_obj - timedelta(days=1)).strftime("%Y-%m-%d")
            st.rerun()
            
    elif pw != "":
        st.error("❌ 비밀번호가 틀렸습니다.")