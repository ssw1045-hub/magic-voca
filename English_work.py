import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import time

# 1. 화면 설정 (다크모드에서도 무조건 연분홍 배경 + 검은 글씨)
st.set_page_config(page_title="고은이 단어장", layout="centered")

st.markdown("""
<style>
    /* 배경색: 연분홍 */
    .stApp { background-color: #FFF0F5 !important; }
    
    /* [중요] 모든 글자색을 '검정색'으로 강제 고정 (다크모드 방어) */
    h1, h2, h3, p, span, div, label, .stMarkdown, li, .stTable td {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
    }
    
    /* 퀴즈 박스 */
    .quiz-card {
        background-color: #FFFFFF !important;
        padding: 40px;
        border-radius: 25px;
        border: 4px solid #FFB6C1;
        text-align: center;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

st.title("💖 고은이의 마법 단어장")

# 2. 구글 시트 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # 캐시를 완전히 무시하고 새로 가져오기
    df = conn.read(ttl=0) 
    
    if df is None or df.empty:
        st.error("🚨 시트에서 데이터를 가져오지 못했습니다. 구글 시트에 단어를 입력하셨나요?")
        st.stop()
except Exception as e:
    st.error(f"🚨 연결 에러 발생! 아빠, 공유 설정을 확인해주세요: {e}")
    st.stop()

# 3. 데이터 전처리 (상태 칸이 비어있으면 0으로 채움)
if '상태' not in df.columns:
    df['상태'] = 0
df['상태'] = pd.to_numeric(df['상태'], errors='coerce').fillna(0).astype(int)

# 4. 공부할 단어 고르기 (상태가 4 미만인 것들)
targets = df[df['상태'] < 4]

# 화면 구성
tab1, tab2 = st.tabs(["🎯 오늘의 퀴즈", "🔒 아빠 관리창"])

with tab1:
    if len(targets) == 0:
        st.balloons()
        st.success("와! 모든 단어를 다 외웠어요! 고은아 대단해! ✨")
    else:
        # 단어 하나 무작위 추출
        q = targets.sample(1).iloc[0]
        
        st.markdown(f"""
        <div class="quiz-card">
            <h3 style="color: #666;">이 단어의 뜻은?</h3>
            <h1 style="font-size: 70px; color: #000;">{q['영어']}</h1>
        </div>
        """, unsafe_allow_html=True)
        
        ans = st.text_input("한글 뜻을 입력하세요", key="input_word").strip()
        
        if st.button("정답 확인! 🚀"):
            if ans == str(q['한글']).strip():
                # 상태 1 증가 (구글 시트 업데이트)
                idx = df[df['영어'] == q['영어']].index[0]
                df.at[idx, '상태'] = int(df.at[idx, '상태']) + 1
                conn.update(data=df)
                st.success("우와! 정답이야! 💖 다음 단어로 넘어갈게!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("앗! 틀렸어. 다시 한번 생각해보자! 💪")

with tab2:
    if st.text_input("관리자 비밀번호", type="password") == "love317619":
        st.write("### 📊 현재 저장된 단어 리스트")
        st.write(f"총 단어 수: {len(df)}개 / 남은 단어: {len(targets)}개")
        st.dataframe(df)
        if st.button("데이터 강제 새로고침 🔄"):
            st.rerun()
