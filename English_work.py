import streamlit as st
import pandas as pd
import time

# 1. UI 설정 (다크모드 완벽 방어)
st.set_page_config(page_title="고은이 단어장", layout="centered")
st.markdown("<style>.stApp { background-color: #FFF0F5 !important; } * { color: #000000 !important; }</style>", unsafe_allow_html=True)

st.title("💖 고은이의 마법 단어장 (최종)")

# 2. 구글 시트 바로 읽기 (열쇠 필요 없는 방식)
SHEET_ID = "1sbHa2YDMuXtSH2GI37vikcf_oCKKoOXt34SLhL34gzY"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

try:
    # 시트 읽어오기
    df = pd.read_csv(URL)
    
    if df.empty:
        st.error("🚨 시트에 단어가 하나도 없어요! 단어를 채워주세요.")
        st.stop()
        
    # 컬럼 이름 정리
    df.columns = [c.strip() for c in df.columns]
    
    # '상태' 열이 없으면 0으로 만들기
    if '상태' not in df.columns:
        df['상태'] = 0
    df['상태'] = pd.to_numeric(df['상태'], errors='coerce').fillna(0).astype(int)

    # 3. 퀴즈 로직
    targets = df[df['상태'] < 4]
    
    if len(targets) == 0:
        st.success("와! 고은아, 오늘 공부할 단어를 다 마스터했어! 👑")
    else:
        q = targets.sample(1).iloc[0]
        st.markdown(f"<div style='background:white; padding:40px; border-radius:20px; border:4px solid #FFB6C1; text-align:center;'><h1 style='font-size:60px;'>{q['영어']}</h1></div>", unsafe_allow_html=True)
        
        ans = st.text_input("뜻을 입력하세요 (정답 확인 후 Enter)", key="quiz_in").strip()
        if st.button("정답 확인!"):
            if ans == str(q['한글']).strip():
                st.balloons()
                st.success("정답이야! 💖")
                time.sleep(1)
                st.rerun()
            else:
                st.error("앗! 틀렸어. 다시 해보자! 💪")
                
    # 4. 데이터 확인 (표)
    with st.expander("👀 아빠 확인용 (현재 단어 목록)"):
        st.write(df)

except Exception as e:
    st.error(f"🚨 시트를 읽어오지 못했습니다. 원인: {e}")
    st.info("💡 아버님, 시트 공유 설정을 '링크가 있는 모든 사용자'로 바꾸셨는지 확인해주세요!")
