import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import os

# 페이지 설정
st.set_page_config(
    page_title="판매재고관리시스템JK v3.0",
    page_icon="📦",
    layout="wide"
)

# Supabase 연결
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# 관리자 이메일 설정 (secrets에 추가하거나 여기서 직접 설정)
ADMIN_EMAIL = st.secrets.get("ADMIN_EMAIL", "admin@example.com")

# 세션 상태 초기화
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'selected_product' not in st.session_state:
    st.session_state.selected_product = None
if 'selected_customer' not in st.session_state:
    st.session_state.selected_customer = None

# ======================
# 사용자 프로필 관리 함수
# ======================
def ensure_user_profile(email):
    """사용자 프로필이 없으면 생성"""
    try:
        # 테이블 존재 확인 및 프로필 조회
        result = supabase.table('user_profiles').select("*").eq('email', email).execute()
        
        if not result.data:
            # 프로필 생성 (관리자는 자동 승인, 일반 사용자는 승인 대기)
            is_admin = (email == ADMIN_EMAIL)
            supabase.table('user_profiles').insert({
                'email': email,
                'approved': is_admin,
                'is_admin': is_admin
            }).execute()
            return is_admin
        else:
            return result.data[0].get('is_admin', False)
    except Exception as e:
        # 테이블이 없는 경우 자동 생성 시도
        if 'user_profiles' in str(e) and 'not find' in str(e):
            try:
                # 테이블 자동 생성을 위한 초기 데이터 삽입
                is_admin = (email == ADMIN_EMAIL)
                supabase.table('user_profiles').insert({
                    'email': email,
                    'approved': is_admin,
                    'is_admin': is_admin
                }).execute()
                return is_admin
            except:
                # 테이블 생성 실패 시 임시로 관리자만 허용
                st.error("⚠️ user_profiles 테이블을 생성해야 합니다. 아래 SQL을 Supabase에서 실행해주세요.")
                st.code("""
CREATE TABLE user_profiles (
  id BIGSERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  approved BOOLEAN DEFAULT FALSE,
  is_admin BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);
                """, language="sql")
                # 관리자 이메일이면 임시 승인
                return (email == ADMIN_EMAIL)
        return False

# ======================
# 로그인/회원가입 화면
# ======================
def show_login_page():
    st.title("📦 판매재고관리시스템JK v3.0")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["로그인", "회원가입"])
    
    with tab1:
        st.subheader("로그인")
        with st.form("login_form"):
            email = st.text_input("이메일", placeholder="example@email.com")
            password = st.text_input("비밀번호", type="password")
            submitted = st.form_submit_button("로그인", use_container_width=True)
            
            if submitted:
                if not email or not password:
                    st.error("이메일과 비밀번호를 입력해주세요.")
                else:
                    try:
                        response = supabase.auth.sign_in_with_password({
                            "email": email,
                            "password": password
                        })
                        
                        if response.user:
                            # 사용자 프로필 확인
                            try:
                                profile = supabase.table('user_profiles').select("*").eq('email', email).execute()
                                
                                if not profile.data:
                                    # 프로필이 없으면 생성
                                    is_admin = ensure_user_profile(email)
                                    if email != ADMIN_EMAIL:
                                        st.warning("⏳ 관리자의 승인을 기다리고 있습니다. 승인 후 다시 로그인해주세요.")
                                        supabase.auth.sign_out()
                                        st.stop()
                                    else:
                                        # 관리자는 바로 로그인
                                        st.session_state.authenticated = True
                                        st.session_state.user_email = email
                                        st.session_state.is_admin = True
                                        st.success("✅ 관리자 로그인 성공!")
                                        st.rerun()
                                else:
                                    user_profile = profile.data[0]
                                    
                                    # 승인 여부 확인
                                    if not user_profile.get('approved', False):
                                        st.warning("⏳ 관리자의 승인을 기다리고 있습니다. 승인 후 다시 로그인해주세요.")
                                        supabase.auth.sign_out()
                                        st.stop()
                                    
                                    # 로그인 성공
                                    st.session_state.authenticated = True
                                    st.session_state.user_email = email
                                    st.session_state.is_admin = user_profile.get('is_admin', False)
                                    st.success("✅ 로그인 성공!")
                                    st.rerun()
                            except Exception as profile_error:
                                # 테이블이 없는 경우 관리자만 임시 허용
                                if 'user_profiles' in str(profile_error):
                                    if email == ADMIN_EMAIL:
                                        st.session_state.authenticated = True
                                        st.session_state.user_email = email
                                        st.session_state.is_admin = True
                                        st.warning("⚠️ user_profiles 테이블을 생성하고 '⚙️ 사용자 관리' 메뉴를 확인해주세요.")
                                        st.rerun()
                                    else:
                                        st.error("시스템 초기화가 필요합니다. 관리자에게 문의하세요.")
                                else:
                                    st.error(f"프로필 확인 오류: {str(profile_error)}")
                        else:
                            st.error("로그인에 실패했습니다.")
                    except Exception as e:
                        st.error(f"로그인 오류: {str(e)}")
    
    with tab2:
        st.subheader("회원가입")
        st.info("📢 회원가입 후 관리자의 승인이 필요합니다.")
        with st.form("signup_form"):
            new_email = st.text_input("이메일", placeholder="example@email.com", key="signup_email")
            new_password = st.text_input("비밀번호 (최소 6자)", type="password", key="signup_password")
            confirm_password = st.text_input("비밀번호 확인", type="password", key="confirm_password")
            submitted = st.form_submit_button("가입하기", use_container_width=True)
            
            if submitted:
                if not new_email or not new_password:
                    st.error("모든 필드를 입력해주세요.")
                elif len(new_password) < 6:
                    st.error("비밀번호는 최소 6자 이상이어야 합니다.")
                elif new_password != confirm_password:
                    st.error("비밀번호가 일치하지 않습니다.")
                else:
                    try:
                        response = supabase.auth.sign_up({
                            "email": new_email,
                            "password": new_password
                        })
                        
                        if response.user:
                            # 사용자 프로필 생성 (승인 대기 상태)
                            is_admin = (new_email == ADMIN_EMAIL)
                            supabase.table('user_profiles').insert({
                                'email': new_email,
                                'approved': is_admin,  # 관리자는 자동 승인
                                'is_admin': is_admin
                            }).execute()
                            
                            if is_admin:
                                st.success("✅ 관리자 계정이 생성되었습니다! 로그인해주세요.")
                            else:
                                st.success("✅ 회원가입 성공! 관리자의 승인을 기다려주세요.")
                                st.info("승인 후 이메일로 알림을 받으실 수 있습니다.")
                        else:
                            st.error("회원가입에 실패했습니다.")
                    except Exception as e:
                        st.error(f"회원가입 오류: {str(e)}")

# 로그아웃 함수
def logout():
    try:
        supabase.auth.sign_out()
        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.session_state.is_admin = False
        st.rerun()
    except Exception as e:
        st.error(f"로그아웃 오류: {str(e)}")

# ======================
# 인증 확인
# ======================
if not st.session_state.authenticated:
    show_login_page()
    st.stop()

# ======================
# 메인 애플리케이션 (로그인 후)
# ======================

# 사이드바 메뉴
st.sidebar.title("📦 판매재고관리시스템JK")
st.sidebar.markdown(f"👤 **{st.session_state.user_email}**")
if st.session_state.is_admin:
    st.sidebar.markdown("🔑 **관리자**")
if st.sidebar.button("🚪 로그아웃", use_container_width=True):
    logout()

st.sidebar.markdown("---")

# 메뉴 구성 (관리자는 추가 메뉴 표시)
menu_options = ["🏠 대시보드", "📦 제품 관리", "📊 재고 관리", "👥 거래처 관리", "💰 판매 관리", "📈 통계 및 보고서"]
if st.session_state.is_admin:
    menu_options.append("⚙️ 사용자 관리")

menu = st.sidebar.radio("메뉴 선택", menu_options)

# ======================
# 관리자 전용: 사용자 관리
# ======================
if menu == "⚙️ 사용자 관리":
    st.title("⚙️ 사용자 관리")
    
    if not st.session_state.is_admin:
        st.error("❌ 관리자만 접근할 수 있습니다.")
        st.stop()
    
    # 테이블 존재 확인
    try:
        test_query = supabase.table('user_profiles').select("id").limit(1).execute()
    except Exception as e:
        if 'user_profiles' in str(e):
            st.error("❌ user_profiles 테이블이 없습니다. 먼저 테이블을 생성해주세요.")
            st.code("""
-- Supabase SQL Editor에서 실행하세요

CREATE TABLE user_profiles (
  id BIGSERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  approved BOOLEAN DEFAULT FALSE,
  is_admin BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- 관리자 계정 추가
INSERT INTO user_profiles (email, approved, is_admin)
VALUES ('""" + ADMIN_EMAIL + """', true, true);
            """, language="sql")
            st.stop()
    
    tab1, tab2 = st.tabs(["승인 대기", "전체 사용자"])
    
    with tab1:
        st.subheader("승인 대기 중인 사용자")
        
        try:
            pending_users = supabase.table('user_profiles').select("*").eq('approved', False).execute()
            
            if pending_users.data:
                for user in pending_users.data:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"📧 {user['email']}")
                        st.caption(f"가입일: {user['created_at'][:10]}")
                    with col2:
                        if st.button("✅ 승인", key=f"approve_{user['id']}"):
                            try:
                                supabase.table('user_profiles').update({
                                    'approved': True
                                }).eq('id', user['id']).execute()
                                st.success(f"{user['email']} 승인 완료!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"오류: {str(e)}")
                    with col3:
                        if st.button("❌ 거부", key=f"reject_{user['id']}"):
                            try:
                                supabase.table('user_profiles').delete().eq('id', user['id']).execute()
                                st.success(f"{user['email']} 거부 완료!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"오류: {str(e)}")
                    st.markdown("---")
            else:
                st.info("승인 대기 중인 사용자가 없습니다.")
        except Exception as e:
            st.error(f"조회 오류: {str(e)}")
    
    with tab2:
        st.subheader("전체 사용자 목록")
        
        try:
            all_users = supabase.table('user_profiles').select("*").order('created_at', desc=True).execute()
            
            if all_users.data:
                df = pd.DataFrame(all_users.data)
                df = df[['email', 'approved', 'is_admin', 'created_at']]
                df.columns = ['이메일', '승인여부', '관리자', '가입일']
                df['승인여부'] = df['승인여부'].apply(lambda x: '✅' if x else '⏳')
                df['관리자'] = df['관리자'].apply(lambda x: '🔑' if x else '')
                df['가입일'] = df['가입일'].apply(lambda x: x[:10])
                
                st.dataframe(df, use_container_width=True)
                
                with st.expander("사용자 상태 변경"):
                    user_to_modify = st.selectbox(
                        "사용자 선택",
                        options=[u['email'] for u in all_users.data if u['email'] != ADMIN_EMAIL]
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("승인 상태 토글"):
                            user = next(u for u in all_users.data if u['email'] == user_to_modify)
                            supabase.table('user_profiles').update({
                                'approved': not user['approved']
                            }).eq('email', user_to_modify).execute()
                            st.success("상태가 변경되었습니다.")
                            st.rerun()
                    
                    with col2:
                        if st.button("사용자 삭제", type="primary"):
                            supabase.table('user_profiles').delete().eq('email', user_to_modify).execute()
                            st.success("사용자가 삭제되었습니다.")
                            st.rerun()
            else:
                st.info("등록된 사용자가 없습니다.")
        except Exception as e:
            st.error(f"조회 오류: {str(e)}")

# ======================
# 1. 대시보드
# ======================
elif menu == "🏠 대시보드":
    st.title("🏠 대시보드")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # 전체 제품 수
    products = supabase.table('products').select("*").execute()
    col1.metric("전체 제품", len(products.data))
    
    # 재고 부족 제품
    inventory = supabase.table('inventory').select("*, products(*)").execute()
    low_stock = [item for item in inventory.data if item['quantity'] <= item['min_quantity']]
    col2.metric("재고 부족", len(low_stock), delta=f"-{len(low_stock)}", delta_color="inverse")
    
    # 전체 거래처
    customers = supabase.table('customers').select("*").execute()
    col3.metric("전체 거래처", len(customers.data))
    
    # 이번 달 판매 건수
    sales = supabase.table('sales').select("*").execute()
    col4.metric("총 판매 건수", len(sales.data))
    
    st.markdown("---")
    
    # 재고 부족 알림
    if low_stock:
        st.warning(f"⚠️ 재고 부족 제품이 {len(low_stock)}개 있습니다!")
        with st.expander("재고 부족 제품 보기"):
            df_low = pd.DataFrame([{
                '제품코드': item['products']['product_code'],
                '제품명': item['products']['product_name'],
                '현재고': item['quantity'],
                '최소재고': item['min_quantity'],
                '부족수량': item['min_quantity'] - item['quantity']
            } for item in low_stock])
            st.dataframe(df_low, use_container_width=True)

# ======================
# 2. 제품 관리
# ======================
elif menu == "📦 제품 관리":
    st.title("📦 제품 관리")
    
    tab1, tab2, tab3 = st.tabs(["제품 등록", "제품 목록", "엑셀 업로드"])
    
    with tab1:
        st.subheader("새 제품 등록")
        with st.form("product_form"):
            col1, col2 = st.columns(2)
            with col1:
                product_code = st.text_input("제품 코드*", key="prod_code")
                product_name = st.text_input("제품명*", key="prod_name")
                category = st.text_input("카테고리")
            with col2:
                unit_price = st.number_input("단가*", min_value=0, step=1000)
                supplier = st.text_input("공급업체")
                description = st.text_area("설명")
            
            submitted = st.form_submit_button("등록")
            if submitted:
                if not product_code or not product_name or unit_price == 0:
                    st.error("제품 코드, 제품명, 단가는 필수 항목입니다.")
                else:
                    try:
                        # 제품 등록
                        result = supabase.table('products').insert({
                            'product_code': product_code,
                            'product_name': product_name,
                            'category': category,
                            'unit_price': unit_price,
                            'supplier': supplier,
                            'description': description
                        }).execute()
                        
                        # 재고 초기화
                        product_id = result.data[0]['product_id']
                        supabase.table('inventory').insert({
                            'product_id': product_id,
                            'quantity': 0,
                            'min_quantity': 10
                        }).execute()
                        
                        st.success("✅ 제품이 등록되었습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {str(e)}")
    
    with tab2:
        st.subheader("제품 목록")
        
        # 검색
        search = st.text_input("🔍 제품명 검색", key="search_product")
        
        # 데이터 로드
        if search:
            products = supabase.table('products').select("*").ilike('product_name', f'%{search}%').execute()
        else:
            products = supabase.table('products').select("*").order('product_id', desc=True).execute()
        
        if products.data:
            df = pd.DataFrame(products.data)
            df = df[['product_code', 'product_name', 'category', 'unit_price', 'supplier']]
            df.columns = ['제품코드', '제품명', '카테고리', '단가', '공급업체']
            df['단가'] = df['단가'].apply(lambda x: f"{x:,.0f}원")
            
            st.dataframe(df, use_container_width=True)
            
            # 삭제 기능
            with st.expander("제품 삭제"):
                product_to_delete = st.selectbox(
                    "삭제할 제품",
                    options=[p['product_code'] for p in products.data],
                    format_func=lambda x: next(p['product_name'] for p in products.data if p['product_code'] == x)
                )
                if st.button("삭제", type="primary"):
                    product_id = next(p['product_id'] for p in products.data if p['product_code'] == product_to_delete)
                    supabase.table('products').delete().eq('product_id', product_id).execute()
                    st.success("제품이 삭제되었습니다.")
                    st.rerun()
        else:
            st.info("등록된 제품이 없습니다.")
    
    with tab3:
        st.subheader("엑셀 파일로 제품 일괄 등록")
        st.info("📋 엑셀 형식: 제품코드 | 제품명 | 카테고리 | 단가 | 공급업체 | 설명")
        
        uploaded_file = st.file_uploader("엑셀 파일 선택", type=['xlsx', 'xls'])
        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            st.write("미리보기:", df.head())
            
            if st.button("업로드"):
                success = 0
                errors = []
                for idx, row in df.iterrows():
                    try:
                        result = supabase.table('products').insert({
                            'product_code': str(row[0]),
                            'product_name': str(row[1]),
                            'category': str(row[2]) if pd.notna(row[2]) else '',
                            'unit_price': float(row[3]) if pd.notna(row[3]) else 0,
                            'supplier': str(row[4]) if pd.notna(row[4]) else '',
                            'description': str(row[5]) if pd.notna(row[5]) else ''
                        }).execute()
                        
                        product_id = result.data[0]['product_id']
                        supabase.table('inventory').insert({
                            'product_id': product_id,
                            'quantity': 0
                        }).execute()
                        success += 1
                    except Exception as e:
                        errors.append(f"행 {idx+2}: {str(e)}")
                
                st.success(f"✅ {success}건 등록 완료")
                if errors:
                    st.error(f"❌ {len(errors)}건 실패")
                    with st.expander("오류 상세"):
                        for err in errors[:10]:
                            st.text(err)
                st.rerun()

# ======================
# 3. 재고 관리
# ======================
elif menu == "📊 재고 관리":
    st.title("📊 재고 관리")
    
    tab1, tab2 = st.tabs(["입/출고 처리", "재고 현황"])
    
    with tab1:
        st.subheader("입/출고 처리")
        
        products = supabase.table('products').select("*").execute()
        if products.data:
            col1, col2 = st.columns(2)
            
            with col1:
                selected_product = st.selectbox(
                    "제품 선택",
                    options=[p['product_id'] for p in products.data],
                    format_func=lambda x: f"{next(p['product_code'] for p in products.data if p['product_id'] == x)} - {next(p['product_name'] for p in products.data if p['product_id'] == x)}"
                )
                quantity = st.number_input("수량", min_value=1, value=1)
                notes = st.text_input("비고")
            
            with col2:
                trans_type = st.radio("처리 유형", ["입고", "출고"])
                st.write("")
                
                if st.button(f"{trans_type} 처리", type="primary"):
                    try:
                        # 현재 재고 확인
                        inv = supabase.table('inventory').select("*").eq('product_id', selected_product).execute()
                        current_qty = inv.data[0]['quantity']
                        
                        if trans_type == "출고" and current_qty < quantity:
                            st.error(f"재고 부족! 현재고: {current_qty}")
                        else:
                            new_qty = current_qty + quantity if trans_type == "입고" else current_qty - quantity
                            
                            # 재고 업데이트
                            supabase.table('inventory').update({
                                'quantity': new_qty,
                                'last_updated': datetime.now().isoformat()
                            }).eq('product_id', selected_product).execute()
                            
                            # 거래 기록
                            supabase.table('transactions').insert({
                                'product_id': selected_product,
                                'transaction_type': trans_type,
                                'quantity': quantity,
                                'notes': notes
                            }).execute()
                            
                            st.success(f"✅ {trans_type} 처리 완료! 현재고: {new_qty}")
                            st.rerun()
                    except Exception as e:
                        st.error(f"오류: {str(e)}")
    
    with tab2:
        st.subheader("재고 현황")
        
        inventory = supabase.table('inventory').select("*, products(*)").execute()
        
        if inventory.data:
            df = pd.DataFrame([{
                '제품코드': item['products']['product_code'],
                '제품명': item['products']['product_name'],
                '현재고': item['quantity'],
                '최소재고': item['min_quantity'],
                '위치': item.get('location', ''),
                '최종수정일': item['last_updated'][:16] if item['last_updated'] else ''
            } for item in inventory.data])
            
            # 재고 부족 강조
            def highlight_low_stock(row):
                if row['현재고'] <= row['최소재고']:
                    return ['background-color: #ffcdd2'] * len(row)
                return [''] * len(row)
            
            styled_df = df.style.apply(highlight_low_stock, axis=1)
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.info("재고 정보가 없습니다.")

# ======================
# 4. 거래처 관리
# ======================
elif menu == "👥 거래처 관리":
    st.title("👥 거래처 관리")
    
    tab1, tab2, tab3 = st.tabs(["거래처 등록", "거래처 목록", "엑셀 업로드"])
    
    with tab1:
        st.subheader("새 거래처 등록")
        with st.form("customer_form"):
            col1, col2 = st.columns(2)
            with col1:
                customer_code = st.text_input("거래처 코드*")
                customer_name = st.text_input("거래처명*")
                contact = st.text_input("연락처")
            with col2:
                email = st.text_input("이메일")
                address = st.text_area("주소")
            
            submitted = st.form_submit_button("등록")
            if submitted:
                if not customer_code or not customer_name:
                    st.error("거래처 코드와 거래처명은 필수입니다.")
                else:
                    try:
                        supabase.table('customers').insert({
                            'customer_code': customer_code,
                            'customer_name': customer_name,
                            'contact': contact,
                            'email': email,
                            'address': address
                        }).execute()
                        st.success("✅ 거래처가 등록되었습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {str(e)}")
    
    with tab2:
        st.subheader("거래처 목록")
        
        search = st.text_input("🔍 거래처명 검색", key="search_customer")
        
        if search:
            customers = supabase.table('customers').select("*").ilike('customer_name', f'%{search}%').execute()
        else:
            customers = supabase.table('customers').select("*").order('customer_id', desc=True).execute()
        
        if customers.data:
            df = pd.DataFrame(customers.data)
            df = df[['customer_code', 'customer_name', 'contact', 'email', 'address']]
            df.columns = ['거래처코드', '거래처명', '연락처', '이메일', '주소']
            st.dataframe(df, use_container_width=True)
            
            with st.expander("거래처 삭제"):
                customer_to_delete = st.selectbox(
                    "삭제할 거래처",
                    options=[c['customer_code'] for c in customers.data],
                    format_func=lambda x: next(c['customer_name'] for c in customers.data if c['customer_code'] == x)
                )
                if st.button("삭제", type="primary"):
                    customer_id = next(c['customer_id'] for c in customers.data if c['customer_code'] == customer_to_delete)
                    supabase.table('customers').delete().eq('customer_id', customer_id).execute()
                    st.success("거래처가 삭제되었습니다.")
                    st.rerun()
        else:
            st.info("등록된 거래처가 없습니다.")
    
    with tab3:
        st.subheader("엑셀 파일로 거래처 일괄 등록")
        st.info("📋 엑셀 형식: 거래처코드 | 거래처명 | 연락처 | 이메일 | 주소")
        
        uploaded_file = st.file_uploader("엑셀 파일 선택", type=['xlsx', 'xls'], key="customer_excel")
        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            st.write("미리보기:", df.head())
            
            if st.button("업로드", key="upload_customer"):
                success = 0
                errors = []
                for idx, row in df.iterrows():
                    try:
                        supabase.table('customers').insert({
                            'customer_code': str(row[0]),
                            'customer_name': str(row[1]),
                            'contact': str(row[2]) if pd.notna(row[2]) else '',
                            'email': str(row[3]) if pd.notna(row[3]) else '',
                            'address': str(row[4]) if pd.notna(row[4]) else ''
                        }).execute()
                        success += 1
                    except Exception as e:
                        errors.append(f"행 {idx+2}: {str(e)}")
                
                st.success(f"✅ {success}건 등록 완료")
                if errors:
                    st.error(f"❌ {len(errors)}건 실패")
                st.rerun()

# ======================
# 5. 판매 관리
# ======================
elif menu == "💰 판매 관리":
    st.title("💰 판매 관리")
    
    tab1, tab2 = st.tabs(["판매 등록", "판매 내역"])
    
    with tab1:
        st.subheader("새 판매 등록")
        
        customers = supabase.table('customers').select("*").execute()
        products = supabase.table('products').select("*").execute()
        
        if not customers.data or not products.data:
            st.warning("먼저 거래처와 제품을 등록해주세요.")
        else:
            col1, col2 = st.columns(2)
            
            with col1:
                selected_customer = st.selectbox(
                    "거래처",
                    options=[c['customer_id'] for c in customers.data],
                    format_func=lambda x: f"{next(c['customer_code'] for c in customers.data if c['customer_id'] == x)} - {next(c['customer_name'] for c in customers.data if c['customer_id'] == x)}"
                )
                
                selected_product = st.selectbox(
                    "제품",
                    options=[p['product_id'] for p in products.data],
                    format_func=lambda x: f"{next(p['product_code'] for p in products.data if p['product_id'] == x)} - {next(p['product_name'] for p in products.data if p['product_id'] == x)}"
                )
            
            with col2:
                quantity = st.number_input("수량", min_value=1, value=1)
                
                # 자동으로 단가 표시
                default_price = next((p['unit_price'] for p in products.data if p['product_id'] == selected_product), 0)
                unit_price = st.number_input("단가", min_value=0, value=int(default_price), step=1000)
            
            notes = st.text_area("비고")
            
            subtotal = quantity * unit_price
            st.info(f"💵 판매금액: {subtotal:,.0f}원")
            
            if st.button("판매 등록", type="primary"):
                try:
                    # 재고 확인
                    inv = supabase.table('inventory').select("*").eq('product_id', selected_product).execute()
                    current_qty = inv.data[0]['quantity']
                    
                    if current_qty < quantity:
                        if not st.checkbox(f"재고 부족 (현재: {current_qty}). 마이너스 재고로 진행하시겠습니까?"):
                            st.stop()
                    
                    # 판매 등록
                    sale = supabase.table('sales').insert({
                        'customer_id': selected_customer,
                        'total_amount': subtotal,
                        'notes': notes
                    }).execute()
                    
                    sale_id = sale.data[0]['sale_id']
                    
                    # 판매 상세
                    supabase.table('sale_details').insert({
                        'sale_id': sale_id,
                        'product_id': selected_product,
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'subtotal': subtotal
                    }).execute()
                    
                    # 재고 차감
                    new_qty = current_qty - quantity
                    supabase.table('inventory').update({
                        'quantity': new_qty
                    }).eq('product_id', selected_product).execute()
                    
                    # 거래 기록
                    supabase.table('transactions').insert({
                        'product_id': selected_product,
                        'transaction_type': '판매',
                        'quantity': quantity,
                        'notes': f"판매번호: {sale_id}"
                    }).execute()
                    
                    st.success(f"✅ 판매가 등록되었습니다! (판매금액: {subtotal:,.0f}원)")
                    st.rerun()
                except Exception as e:
                    st.error(f"오류: {str(e)}")
    
    with tab2:
        st.subheader("판매 내역 (최근 100건)")
        
        sales = supabase.table('sales').select("*, customers(*), sale_details(*, products(*))").order('sale_id', desc=True).limit(100).execute()
        
        if sales.data:
            records = []
            for sale in sales.data:
                for detail in sale['sale_details']:
                    records.append({
                        '판매ID': sale['sale_id'],
                        '판매일': sale['sale_date'][:16],
                        '거래처': sale['customers']['customer_name'],
                        '제품명': detail['products']['product_name'],
                        '수량': detail['quantity'],
                        '단가': f"{detail['unit_price']:,.0f}",
                        '합계': f"{detail['subtotal']:,.0f}",
                        '상태': sale['payment_status']
                    })
            
            df = pd.DataFrame(records)
            st.dataframe(df, use_container_width=True)
            
            with st.expander("판매 취소"):
                st.warning("⚠️ 판매를 취소하면 재고가 복구됩니다.")
                sale_to_delete = st.number_input("취소할 판매 ID", min_value=1, step=1)
                if st.button("취소", type="primary"):
                    try:
                        # 판매 상세 조회
                        detail = supabase.table('sale_details').select("*").eq('sale_id', sale_to_delete).execute()
                        if detail.data:
                            product_id = detail.data[0]['product_id']
                            quantity = detail.data[0]['quantity']
                            
                            # 재고 복구
                            current = supabase.table('inventory').select('quantity').eq('product_id', product_id).execute()
                            supabase.table('inventory').update({
                                'quantity': current.data[0]['quantity'] + quantity
                            }).eq('product_id', product_id).execute()
                            
                            # 판매 삭제
                            supabase.table('sales').delete().eq('sale_id', sale_to_delete).execute()
                            
                            st.success("판매가 취소되고 재고가 복구되었습니다.")
                            st.rerun()
                    except Exception as e:
                        st.error(f"오류: {str(e)}")
        else:
            st.info("판매 내역이 없습니다.")

# ======================
# 6. 통계 및 보고서
# ======================
elif menu == "📈 통계 및 보고서":
    st.title("📈 통계 및 보고서")
    
    report_type = st.selectbox(
        "보고서 선택",
        ["재고 부족 제품", "월별 매출 통계", "입/출고 내역"]
    )
    
    if report_type == "재고 부족 제품":
        st.subheader("📉 재고 부족 제품 현황")
        
        inventory = supabase.table('inventory').select("*, products(*)").execute()
        low_stock = [item for item in inventory.data if item['quantity'] <= item['min_quantity']]
        
        if low_stock:
            df = pd.DataFrame([{
                '제품코드': item['products']['product_code'],
                '제품명': item['products']['product_name'],
                '현재고': item['quantity'],
                '최소재고': item['min_quantity'],
                '부족수량': item['min_quantity'] - item['quantity']
            } for item in low_stock])
            
            df = df.sort_values('부족수량', ascending=False)
            st.dataframe(df, use_container_width=True)
        else:
            st.success("✅ 재고 부족 제품이 없습니다!")
    
    elif report_type == "월별 매출 통계":
        st.subheader("📊 월별 매출 통계")
        
        sales = supabase.table('sales').select("*").execute()
        
        if sales.data:
            df = pd.DataFrame(sales.data)
            df['sale_date'] = pd.to_datetime(df['sale_date'])
            df['month'] = df['sale_date'].dt.to_period('M')
            
            monthly = df.groupby('month').agg({
                'sale_id': 'count',
                'total_amount': 'sum'
            }).reset_index()
            
            monthly.columns = ['월', '판매건수', '매출액']
            monthly['매출액'] = monthly['매출액'].apply(lambda x: f"{x:,.0f}원")
            
            st.dataframe(monthly, use_container_width=True)
            
            total = df['total_amount'].sum()
            st.metric("총 매출액", f"{total:,.0f}원")
        else:
            st.info("판매 데이터가 없습니다.")
    
    elif report_type == "입/출고 내역":
        st.subheader("📋 입/출고 내역 (최근 100건)")
        
        trans = supabase.table('transactions').select("*, products(*)").order('transaction_id', desc=True).limit(100).execute()
        
        if trans.data:
            df = pd.DataFrame([{
                '일시': t['transaction_date'][:19],
                '제품코드': t['products']['product_code'],
                '제품명': t['products']['product_name'],
                '구분': t['transaction_type'],
                '수량': t['quantity'],
                '비고': t.get('notes', '')
            } for t in trans.data])
            
            st.dataframe(df, use_container_width=True)
        else:
            st.info("거래 내역이 없습니다.")

# 푸터
st.sidebar.markdown("---")
st.sidebar.caption("© JK이러닝연구소 2025")
st.sidebar.caption("판매재고관리시스템JK v3.0 (Streamlit)")
