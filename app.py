import streamlit as st
import pandas as pd
import json
import datetime
import os
import re
from typing import Dict, List, Any
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
import uuid
import hashlib

# Configuração de autenticação
def check_password():
    """Retorna True se o usuário inseriu a senha correta"""
    
    def password_entered():
        """Verifica se a senha está correta"""
        # Hash da senha: "rh2025" (você pode mudar depois)
        # Para gerar novo hash: hashlib.sha256("sua_senha".encode()).hexdigest()
        correct_password_hash = "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"
        
        entered_password = st.session_state["password"]
        entered_hash = hashlib.sha256(entered_password.encode()).hexdigest()
        
        if entered_hash == correct_password_hash:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Remove a senha da sessão por segurança
        else:
            st.session_state["password_correct"] = False
    
    # Primeira execução ou senha não verificada
    if "password_correct" not in st.session_state:
        st.title("🔒 Acesso Restrito")
        st.write("Sistema de Monitoramento de Atestados Médicos")
        st.write("---")
        st.text_input(
            "Digite a senha de acesso:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.info("💡 Senha padrão: **rh2025**")
        st.caption("Entre em contato com o administrador se esqueceu a senha.")
        return False
    
    # Senha incorreta
    elif not st.session_state["password_correct"]:
        st.title("🔒 Acesso Restrito")
        st.write("Sistema de Monitoramento de Atestados Médicos")
        st.write("---")
        st.text_input(
            "Digite a senha de acesso:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("❌ Senha incorreta. Tente novamente.")
        st.caption("Entre em contato com o administrador se esqueceu a senha.")
        return False
    
    # Senha correta
    else:
        return True

class MedicalStorage:
    """Sistema de armazenamento para dados de médicos e atestados"""
    
    def __init__(self, data_file="data/medical_data.json", backup_dir="backups/"):
        self.data_file = data_file
        self.backup_dir = backup_dir
        self._ensure_directories()
        self.load_data()
    
    def _ensure_directories(self):
        """Garante que os diretórios necessários existam"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def load_data(self):
        """Carrega os dados do arquivo JSON"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.data = {
                "doctors": {},
                "employees": {},
                "certificates": {},
                "last_update": datetime.datetime.now().isoformat()
            }
            self.save_data()
    
    def save_data(self):
        """Salva os dados no arquivo JSON"""
        self.data["last_update"] = datetime.datetime.now().isoformat()
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def create_backup(self):
        """Cria um backup dos dados"""
        backup_file = f"{self.backup_dir}backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        return backup_file

    def add_doctor(self, crm: str, name: str, specialty: str = "", phone: str = "", email: str = ""):
        """Adiciona um médico ao sistema"""
        for doctor_id, doctor_data in self.data["doctors"].items():
            if doctor_data["crm"].lower() == crm.lower():
                st.warning(f"Médico com CRM {crm} já está cadastrado!")
                return doctor_id
        
        doctor_id = str(uuid.uuid4())
        self.data["doctors"][doctor_id] = {
            "crm": crm,
            "name": name,
            "specialty": specialty,
            "phone": phone,
            "email": email,
            "total_attendances": 0,
            "total_certificates": 0,
            "created_at": datetime.datetime.now().isoformat(),
            "last_attendance": None
        }
        self.save_data()
        return doctor_id

    def update_doctor(self, doctor_id: str, **kwargs):
        """Atualiza dados de um médico"""
        if doctor_id in self.data["doctors"]:
            for key, value in kwargs.items():
                if value:
                    self.data["doctors"][doctor_id][key] = value
            self.save_data()
            return True
        return False

    def delete_doctor(self, doctor_id: str):
        """Remove um médico do sistema"""
        if doctor_id in self.data["doctors"]:
            doctor_certificates = sum(1 for cert in self.data["certificates"].values() 
                                    if cert["doctor_id"] == doctor_id)
            
            if doctor_certificates > 0:
                return False, f"Médico possui {doctor_certificates} atendimentos registrados. Não pode ser excluído."
            
            del self.data["doctors"][doctor_id]
            self.save_data()
            return True, "Médico excluído com sucesso!"
        return False, "Médico não encontrado!"

    def add_employee(self, registration: str, name: str, department: str = ""):
        """Adiciona um funcionário ao sistema"""
        for employee_id, employee_data in self.data["employees"].items():
            if employee_data["registration"] == registration:
                return employee_id
        
        employee_id = str(uuid.uuid4())
        self.data["employees"][employee_id] = {
            "registration": registration,
            "name": name,
            "department": department,
            "total_attendances": 0,
            "total_certificates": 0,
            "created_at": datetime.datetime.now().isoformat()
        }
        self.save_data()
        return employee_id
    
    def add_certificate(self, doctor_id: str, employee_id: str, certificate_date: str, 
                       days_off: int = 0, diagnosis: str = ""):
        """Registra um atestado médico"""
        certificate_id = str(uuid.uuid4())
        
        self.data["certificates"][certificate_id] = {
            "doctor_id": doctor_id,
            "employee_id": employee_id,
            "certificate_date": certificate_date,
            "days_off": days_off,
            "diagnosis": diagnosis,
            "created_at": datetime.datetime.now().isoformat()
        }
        
        if doctor_id in self.data["doctors"]:
            self.data["doctors"][doctor_id]["total_attendances"] += 1
            self.data["doctors"][doctor_id]["total_certificates"] += 1
            self.data["doctors"][doctor_id]["last_attendance"] = certificate_date
        
        if employee_id in self.data["employees"]:
            self.data["employees"][employee_id]["total_attendances"] += 1
            self.data["employees"][employee_id]["total_certificates"] += 1
        
        self.save_data()
        return certificate_id
    
    def get_top_doctors_certificates(self, limit=10):
        """Retorna os médicos que mais emitem atestados"""
        doctors_list = []
        for doctor_id, doctor_data in self.data["doctors"].items():
            doctors_list.append({
                "doctor_id": doctor_id,
                "crm": doctor_data["crm"],
                "name": doctor_data["name"],
                "specialty": doctor_data["specialty"],
                "total_certificates": doctor_data["total_certificates"],
                "total_attendances": doctor_data["total_attendances"],
                "last_attendance": doctor_data.get("last_attendance")
            })
        
        return sorted(doctors_list, key=lambda x: x["total_certificates"], reverse=True)[:limit]
    
    def get_top_employees_certificates(self, limit=10):
        """Retorna os funcionários que mais recebem atestados"""
        employees_list = []
        for employee_id, employee_data in self.data["employees"].items():
            employees_list.append({
                "employee_id": employee_id,
                "registration": employee_data["registration"],
                "name": employee_data["name"],
                "department": employee_data["department"],
                "total_certificates": employee_data["total_certificates"],
                "total_attendances": employee_data["total_attendances"]
            })
        
        return sorted(employees_list, key=lambda x: x["total_certificates"], reverse=True)[:limit]
    
    def get_statistics(self):
        """Retorna estatísticas gerais"""
        total_doctors = len(self.data["doctors"])
        total_employees = len(self.data["employees"])
        total_certificates = len(self.data["certificates"])
        total_attendances = sum(doctor["total_attendances"] for doctor in self.data["doctors"].values())
        
        return {
            "total_doctors": total_doctors,
            "total_employees": total_employees,
            "total_certificates": total_certificates,
            "total_attendances": total_attendances,
            "certificates_per_doctor": total_certificates / total_doctors if total_doctors > 0 else 0,
            "certificates_per_employee": total_certificates / total_employees if total_employees > 0 else 0
        }

def setup_streamlit_app():
    """Configura a aplicação Streamlit"""
    st.set_page_config(
        page_title="Medical Certificate Monitor",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }
        .metric-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 10px;
            border-left: 4px solid #1f77b4;
        }
        </style>
    """, unsafe_allow_html=True)

def main():
    # Verifica autenticação ANTES de mostrar qualquer coisa
    if not check_password():
        return
    
    setup_streamlit_app()
    storage = MedicalStorage()
    
    st.title("🏥 Medical Certificate Monitor")
    st.markdown("**Sistema de Monitoramento de Atestados Médicos**")
    st.markdown("---")
    
    st.sidebar.title("📋 Navegação")
    page = st.sidebar.radio("Selecione a página:", [
        "📊 Dashboard", 
        "👨‍⚕️ Gerenciar Médicos", 
        "👥 Cadastrar Funcionário", 
        "📝 Registrar Atendimento",
        "📁 Importar Dados",
        "📥 Importar Relatório Completo",
        "💾 Backup & Exportar"
    ])
    
    if page == "📊 Dashboard":
        show_dashboard(storage)
    elif page == "👨‍⚕️ Gerenciar Médicos":
        show_doctor_management(storage)
    elif page == "👥 Cadastrar Funcionário":
        show_employee_registration(storage)
    elif page == "📝 Registrar Atendimento":
        show_attendance_registration(storage)
    elif page == "📁 Importar Dados":
        show_data_import(storage)
    elif page == "📥 Importar Relatório Completo":
        show_complete_report_import(storage)
    elif page == "💾 Backup & Exportar":
        show_backup_management(storage)

def show_dashboard(storage):
    """Exibe o dashboard principal"""
    st.header("📊 Dashboard de Monitoramento")
    
    stats = storage.get_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👨‍⚕️ Total de Médicos", stats["total_doctors"])
    with col2:
        st.metric("👥 Total de Funcionários", stats["total_employees"])
    with col3:
        st.metric("📝 Total de Atestados", stats["total_certificates"])
    with col4:
        st.metric("🏥 Total de Atendimentos", stats["total_attendances"])
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👨‍⚕️ Top 10 Médicos - Mais Atestados Emitidos")
        top_doctors = storage.get_top_doctors_certificates(10)
        if top_doctors:
            df_doctors = pd.DataFrame(top_doctors)
            st.dataframe(
                df_doctors[['name', 'crm', 'specialty', 'total_certificates']],
                column_config={
                    'name': 'Nome',
                    'crm': 'CRM',
                    'specialty': 'Especialidade',
                    'total_certificates': 'Total Atestados'
                },
                hide_index=True,
                use_container_width=True
            )
            
            fig = px.bar(df_doctors.head(10), x='name', y='total_certificates',
                        title='Atestados por Médico',
                        labels={'name': 'Médico', 'total_certificates': 'Atestados'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado disponível ainda.")
    
    with col2:
        st.subheader("👥 Top 10 Funcionários - Mais Atestados Recebidos")
        top_employees = storage.get_top_employees_certificates(10)
        if top_employees:
            df_employees = pd.DataFrame(top_employees)
            st.dataframe(
                df_employees[['name', 'registration', 'department', 'total_certificates']],
                column_config={
                    'name': 'Nome',
                    'registration': 'Matrícula',
                    'department': 'Departamento',
                    'total_certificates': 'Total Atestados'
                },
                hide_index=True,
                use_container_width=True
            )
            
            fig = px.bar(df_employees.head(10), x='name', y='total_certificates',
                        title='Atestados por Funcionário',
                        labels={'name': 'Funcionário', 'total_certificates': 'Atestados'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado disponível ainda.")

def show_doctor_management(storage):
    """Gerenciamento de médicos"""
    st.header("👨‍⚕️ Gerenciamento de Médicos")
    
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar", "📋 Lista", "✏️ Editar/Excluir"])
    
    with tab1:
        show_doctor_registration(storage)
    
    with tab2:
        show_doctors_list(storage)
    
    with tab3:
        show_doctor_edit_delete(storage)

def show_doctor_registration(storage):
    """Formulário de cadastro de médicos"""
    st.subheader("Cadastrar Novo Médico")
    
    with st.form("doctor_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            crm = st.text_input("CRM*", placeholder="Ex: 12345/SP")
            name = st.text_input("Nome Completo*", placeholder="Dr. João Silva")
            specialty = st.text_input("Especialidade", placeholder="Clínico Geral")
        
        with col2:
            phone = st.text_input("Telefone", placeholder="(11) 99999-9999")
            email = st.text_input("Email", placeholder="medico@exemplo.com")
        
        submitted = st.form_submit_button("💾 Cadastrar Médico", use_container_width=True)
        
        if submitted:
            if crm and name:
                doctor_id = storage.add_doctor(crm, name, specialty, phone, email)
                if doctor_id:
                    st.success(f"✅ Médico {name} cadastrado com sucesso!")
                    st.balloons()
            else:
                st.error("❌ Preencha os campos obrigatórios (*)")

def show_doctors_list(storage):
    """Lista de médicos cadastrados"""
    st.subheader("Médicos Cadastrados")
    
    doctors = storage.data["doctors"]
    
    if not doctors:
        st.info("📝 Nenhum médico cadastrado ainda.")
        return
    
    search_term = st.text_input("🔍 Buscar:", placeholder="Nome, CRM ou especialidade")
    
    doctors_list = []
    for doctor_id, doctor_data in doctors.items():
        doctors_list.append({
            "CRM": doctor_data["crm"],
            "Nome": doctor_data["name"],
            "Especialidade": doctor_data["specialty"],
            "Telefone": doctor_data.get("phone", "-"),
            "Total Atestados": doctor_data["total_certificates"],
            "Total Atendimentos": doctor_data["total_attendances"]
        })
    
    df = pd.DataFrame(doctors_list)
    
    if search_term:
        mask = (df['Nome'].str.contains(search_term, case=False, na=False)) | \
               (df['CRM'].str.contains(search_term, case=False, na=False)) | \
               (df['Especialidade'].str.contains(search_term, case=False, na=False))
        df = df[mask]
    
    if len(df) > 0:
        st.dataframe(df, hide_index=True, use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Médicos", len(df))
        with col2:
            st.metric("Atestados Emitidos", df['Total Atestados'].sum())
        with col3:
            st.metric("Média por Médico", f"{df['Total Atestados'].mean():.1f}")

def show_doctor_edit_delete(storage):
    """Editar/excluir médicos"""
    st.subheader("Editar ou Excluir Médicos")
    
    doctors = storage.data["doctors"]
    
    if not doctors:
        st.info("Nenhum médico cadastrado.")
        return
    
    doctor_options = {f"{doc['name']} - CRM: {doc['crm']}": doc_id 
                     for doc_id, doc in doctors.items()}
    
    selected = st.selectbox("Selecione o médico:", list(doctor_options.keys()))
    doctor_id = doctor_options[selected]
    doctor_data = doctors[doctor_id]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✏️ Editar Dados")
        with st.form("edit_form"):
            new_name = st.text_input("Nome", value=doctor_data["name"])
            new_specialty = st.text_input("Especialidade", value=doctor_data["specialty"])
            new_phone = st.text_input("Telefone", value=doctor_data.get("phone", ""))
            new_email = st.text_input("Email", value=doctor_data.get("email", ""))
            
            if st.form_submit_button("💾 Atualizar"):
                if storage.update_doctor(doctor_id, name=new_name, specialty=new_specialty,
                                       phone=new_phone, email=new_email):
                    st.success("✅ Dados atualizados!")
                    st.rerun()
    
    with col2:
        st.subheader("📋 Informações Atuais")
        st.write(f"**CRM:** {doctor_data['crm']}")
        st.write(f"**Nome:** {doctor_data['name']}")
        st.write(f"**Especialidade:** {doctor_data['specialty']}")
        st.write(f"**Atendimentos:** {doctor_data['total_attendances']}")
        st.write(f"**Atestados:** {doctor_data['total_certificates']}")
        
        st.markdown("---")
        if st.button("🗑️ Excluir Médico", type="secondary"):
            success, msg = storage.delete_doctor(doctor_id)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

def show_employee_registration(storage):
    """Cadastro de funcionários"""
    st.header("👥 Cadastrar Funcionário")
    
    with st.form("employee_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            registration = st.text_input("Matrícula*", placeholder="Ex: 12345")
            name = st.text_input("Nome Completo*", placeholder="Maria Silva")
        
        with col2:
            department = st.text_input("Departamento", placeholder="RH, TI, etc.")
        
        submitted = st.form_submit_button("💾 Cadastrar Funcionário", use_container_width=True)
        
        if submitted:
            if registration and name:
                employee_id = storage.add_employee(registration, name, department)
                if employee_id:
                    st.success(f"✅ Funcionário {name} cadastrado!")
                    st.balloons()
            else:
                st.error("❌ Preencha os campos obrigatórios (*)")
    
    st.markdown("---")
    st.subheader("📋 Funcionários Cadastrados")
    
    employees = storage.data["employees"]
    if employees:
        emp_list = []
        for emp_id, emp_data in employees.items():
            emp_list.append({
                "Matrícula": emp_data["registration"],
                "Nome": emp_data["name"],
                "Departamento": emp_data["department"],
                "Total Atestados": emp_data["total_certificates"]
            })
        
        df = pd.DataFrame(emp_list)
        st.dataframe(df, hide_index=True, use_container_width=True)

def show_attendance_registration(storage):
    """Registrar atendimento"""
    st.header("📝 Registrar Atendimento/Atestado")
    
    doctors = storage.data["doctors"]
    employees = storage.data["employees"]
    
    if not doctors:
        st.warning("⚠️ Cadastre médicos antes de registrar atendimentos!")
        return
    
    if not employees:
        st.warning("⚠️ Cadastre funcionários antes de registrar atendimentos!")
        return
    
    with st.form("attendance_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            doctor_options = {f"{doc['name']} - CRM: {doc['crm']}": doc_id 
                            for doc_id, doc in doctors.items()}
            selected_doctor = st.selectbox("Médico*", list(doctor_options.keys()))
            doctor_id = doctor_options[selected_doctor]
            
            certificate_date = st.date_input("Data do Atestado*", datetime.date.today())
            days_off = st.number_input("Dias de Afastamento", min_value=0, value=1)
        
        with col2:
            employee_options = {f"{emp['name']} - Mat: {emp['registration']}": emp_id 
                              for emp_id, emp in employees.items()}
            selected_employee = st.selectbox("Funcionário*", list(employee_options.keys()))
            employee_id = employee_options[selected_employee]
            
            diagnosis = st.text_area("Diagnóstico/Observações", placeholder="Opcional")
        
        submitted = st.form_submit_button("💾 Registrar Atendimento", use_container_width=True)
        
        if submitted:
            cert_id = storage.add_certificate(
                doctor_id, employee_id, 
                certificate_date.isoformat(), 
                days_off, diagnosis
            )
            if cert_id:
                st.success("✅ Atendimento registrado com sucesso!")
                st.balloons()

def show_data_import(storage):
    """Importar dados de funcionários e médicos"""
    st.header("📁 Importar Dados")
    
    # Seletor de tipo de importação
    import_type = st.radio(
        "O que deseja importar?",
        ["👥 Funcionários", "👨‍⚕️ Médicos"],
        horizontal=True
    )
    
    if import_type == "👥 Funcionários":
        import_employees(storage)
    else:
        import_doctors(storage)

def import_employees(storage):
    """Importar dados de funcionários"""
    st.subheader("📁 Importar Funcionários")
    
def import_employees(storage):
    """Importar dados de funcionários"""
    st.subheader("📁 Importar Funcionários")
    
    st.info("💡 Importe funcionários do Sonne ou qualquer sistema em formato CSV ou Excel")
    
    # Instruções
    with st.expander("📖 Como preparar o arquivo para importação"):
        st.markdown("""
        ### Formato do Arquivo
        
        O arquivo deve conter as seguintes colunas (a ordem não importa):
        - **matricula** ou **matrícula** ou **registration**: Matrícula do funcionário
        - **nome** ou **name**: Nome completo do funcionário
        - **departamento** ou **department** ou **setor**: Departamento (opcional)
        
        ### Exemplo de CSV:
        ```
        matricula,nome,departamento
        12345,João Silva,RH
        12346,Maria Santos,TI
        12347,Pedro Costa,Financeiro
        ```
        
        ### Exemplo de Excel:
        | matricula | nome | departamento |
        |-----------|------|--------------|
        | 12345 | João Silva | RH |
        | 12346 | Maria Santos | TI |
        | 12347 | Pedro Costa | Financeiro |
        
        ⚠️ **Importante:** Funcionários com matrícula já cadastrada serão ignorados.
        """)
    
    uploaded_file = st.file_uploader(
        "Escolha um arquivo CSV ou Excel", 
        type=['csv', 'xlsx', 'xls'],
        help="Formatos aceitos: CSV, Excel (.xlsx, .xls)"
    )
    
    if uploaded_file:
        try:
            # Lê o arquivo
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ Arquivo carregado: {uploaded_file.name}")
            st.write(f"**Total de linhas:** {len(df)}")
            
            # Mostra preview
            st.subheader("👀 Preview dos Dados")
            st.dataframe(df.head(10), use_container_width=True)
            
            # Normaliza nomes das colunas
            df.columns = df.columns.str.lower().str.strip()
            
            # Identifica as colunas
            matricula_col = None
            nome_col = None
            departamento_col = None
            
            for col in df.columns:
                if col in ['matricula', 'matrícula', 'registration', 'mat']:
                    matricula_col = col
                elif col in ['nome', 'name', 'funcionario', 'funcionário']:
                    nome_col = col
                elif col in ['departamento', 'department', 'setor', 'area', 'área']:
                    departamento_col = col
            
            if not matricula_col or not nome_col:
                st.error("❌ **Erro:** Arquivo deve conter colunas 'matricula' e 'nome'")
                st.info("Colunas encontradas: " + ", ".join(df.columns))
                return
            
            st.success(f"✅ Colunas identificadas: {matricula_col} e {nome_col}")
            if departamento_col:
                st.success(f"✅ Coluna de departamento: {departamento_col}")
            
            # Botão de confirmação
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col2:
                if st.button("📥 IMPORTAR DADOS", type="primary", use_container_width=True):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    imported = 0
                    duplicated = 0
                    errors = 0
                    
                    for idx, row in df.iterrows():
                        try:
                            matricula = str(row[matricula_col]).strip()
                            nome = str(row[nome_col]).strip()
                            departamento = str(row[departamento_col]).strip() if departamento_col and pd.notna(row[departamento_col]) else ""
                            
                            # Verifica se já existe
                            exists = False
                            for emp_id, emp_data in storage.data["employees"].items():
                                if emp_data["registration"] == matricula:
                                    exists = True
                                    duplicated += 1
                                    break
                            
                            if not exists and matricula and nome:
                                storage.add_employee(matricula, nome, departamento)
                                imported += 1
                            elif not matricula or not nome:
                                errors += 1
                            
                            # Atualiza progresso
                            progress = (idx + 1) / len(df)
                            progress_bar.progress(progress)
                            status_text.text(f"Processando linha {idx + 1} de {len(df)}...")
                        
                        except Exception as e:
                            errors += 1
                            st.warning(f"Erro na linha {idx + 1}: {str(e)}")
                    
                    progress_bar.progress(1.0)
                    status_text.empty()
                    
                    # Relatório final
                    st.markdown("---")
                    st.subheader("📊 Relatório de Importação")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("✅ Importados", imported)
                    with col2:
                        st.metric("⚠️ Duplicados", duplicated)
                    with col3:
                        st.metric("❌ Erros", errors)
                    
                    if imported > 0:
                        st.success(f"🎉 Importação concluída! {imported} funcionários foram cadastrados.")
                        st.balloons()
                    
                    if duplicated > 0:
                        st.warning(f"⚠️ {duplicated} funcionários já estavam cadastrados e foram ignorados.")
                    
                    if errors > 0:
                        st.error(f"❌ {errors} linhas tiveram erro no processamento.")
        
        except Exception as e:
            st.error(f"❌ Erro ao processar arquivo: {str(e)}")
            st.info("Verifique se o arquivo está no formato correto.")
    
    # Opção de baixar modelo
    st.markdown("---")
    st.subheader("📥 Baixar Modelo de Importação")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gera CSV modelo
        modelo_csv = """matricula,nome,departamento
12345,João da Silva,Recursos Humanos
12346,Maria Santos,Tecnologia da Informação
12347,Pedro Costa,Financeiro
12348,Ana Oliveira,Operações
12349,Carlos Souza,Marketing"""
        
        st.download_button(
            label="📄 Baixar Modelo CSV",
            data=modelo_csv,
            file_name="modelo_funcionarios.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Gera Excel modelo
        df_modelo = pd.DataFrame({
            'matricula': ['12345', '12346', '12347', '12348', '12349'],
            'nome': ['João da Silva', 'Maria Santos', 'Pedro Costa', 'Ana Oliveira', 'Carlos Souza'],
            'departamento': ['Recursos Humanos', 'Tecnologia da Informação', 'Financeiro', 'Operações', 'Marketing']
        })
        
        # Converte para Excel em memória
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_modelo.to_excel(writer, index=False, sheet_name='Funcionários')
        excel_data = output.getvalue()
        
        st.download_button(
            label="📊 Baixar Modelo Excel",
            data=excel_data,
            file_name="modelo_funcionarios.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

def import_doctors(storage):
    """Importar dados de médicos"""
    st.subheader("📁 Importar Médicos")
    
    st.info("💡 Importe médicos de qualquer sistema em formato CSV ou Excel")
    
    # Instruções
    with st.expander("📖 Como preparar o arquivo para importação"):
        st.markdown("""
        ### Formato do Arquivo
        
        O arquivo deve conter as seguintes colunas (a ordem não importa):
        - **crm**: CRM do médico (Ex: 12345/SP) - OBRIGATÓRIO
        - **nome** ou **name**: Nome completo do médico - OBRIGATÓRIO
        - **especialidade** ou **specialty**: Especialidade médica (opcional)
        - **telefone** ou **phone**: Telefone de contato (opcional)
        - **email**: Email do médico (opcional)
        
        ### Exemplo de CSV:
        ```
        crm,nome,especialidade,telefone,email
        12345/SP,Dr. João Silva,Clínico Geral,(11) 99999-9999,joao@email.com
        23456/RJ,Dra. Maria Santos,Cardiologia,(21) 98888-8888,maria@email.com
        34567/MG,Dr. Pedro Costa,Ortopedia,(31) 97777-7777,pedro@email.com
        ```
        
        ### Exemplo de Excel:
        | crm | nome | especialidade | telefone | email |
        |-----|------|---------------|----------|-------|
        | 12345/SP | Dr. João Silva | Clínico Geral | (11) 99999-9999 | joao@email.com |
        | 23456/RJ | Dra. Maria Santos | Cardiologia | (21) 98888-8888 | maria@email.com |
        
        ⚠️ **Importante:** Médicos com CRM já cadastrado serão ignorados.
        """)
    
    uploaded_file = st.file_uploader(
        "Escolha um arquivo CSV ou Excel", 
        type=['csv', 'xlsx', 'xls'],
        help="Formatos aceitos: CSV, Excel (.xlsx, .xls)",
        key="doctor_upload"
    )
    
    if uploaded_file:
        try:
            # Lê o arquivo
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ Arquivo carregado: {uploaded_file.name}")
            st.write(f"**Total de linhas:** {len(df)}")
            
            # Mostra preview
            st.subheader("👀 Preview dos Dados")
            st.dataframe(df.head(10), use_container_width=True)
            
            # Normaliza nomes das colunas
            df.columns = df.columns.str.lower().str.strip()
            
            # Identifica as colunas
            crm_col = None
            nome_col = None
            especialidade_col = None
            telefone_col = None
            email_col = None
            
            for col in df.columns:
                if col in ['crm', 'registro', 'conselho']:
                    crm_col = col
                elif col in ['nome', 'name', 'medico', 'médico']:
                    nome_col = col
                elif col in ['especialidade', 'specialty', 'especializacao', 'especialização']:
                    especialidade_col = col
                elif col in ['telefone', 'phone', 'fone', 'celular']:
                    telefone_col = col
                elif col in ['email', 'e-mail', 'mail']:
                    email_col = col
            
            if not crm_col or not nome_col:
                st.error("❌ **Erro:** Arquivo deve conter colunas 'crm' e 'nome'")
                st.info("Colunas encontradas: " + ", ".join(df.columns))
                return
            
            st.success(f"✅ Colunas identificadas: {crm_col} e {nome_col}")
            if especialidade_col:
                st.success(f"✅ Coluna de especialidade: {especialidade_col}")
            if telefone_col:
                st.success(f"✅ Coluna de telefone: {telefone_col}")
            if email_col:
                st.success(f"✅ Coluna de email: {email_col}")
            
            # Botão de confirmação
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col2:
                if st.button("📥 IMPORTAR MÉDICOS", type="primary", use_container_width=True):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    imported = 0
                    duplicated = 0
                    errors = 0
                    
                    for idx, row in df.iterrows():
                        try:
                            crm = str(row[crm_col]).strip()
                            nome = str(row[nome_col]).strip()
                            especialidade = str(row[especialidade_col]).strip() if especialidade_col and pd.notna(row[especialidade_col]) else ""
                            telefone = str(row[telefone_col]).strip() if telefone_col and pd.notna(row[telefone_col]) else ""
                            email = str(row[email_col]).strip() if email_col and pd.notna(row[email_col]) else ""
                            
                            # Verifica se já existe
                            exists = False
                            for doc_id, doc_data in storage.data["doctors"].items():
                                if doc_data["crm"].lower() == crm.lower():
                                    exists = True
                                    duplicated += 1
                                    break
                            
                            if not exists and crm and nome:
                                storage.add_doctor(crm, nome, especialidade, telefone, email)
                                imported += 1
                            elif not crm or not nome:
                                errors += 1
                            
                            # Atualiza progresso
                            progress = (idx + 1) / len(df)
                            progress_bar.progress(progress)
                            status_text.text(f"Processando linha {idx + 1} de {len(df)}...")
                        
                        except Exception as e:
                            errors += 1
                            st.warning(f"Erro na linha {idx + 1}: {str(e)}")
                    
                    progress_bar.progress(1.0)
                    status_text.empty()
                    
                    # Relatório final
                    st.markdown("---")
                    st.subheader("📊 Relatório de Importação")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("✅ Importados", imported)
                    with col2:
                        st.metric("⚠️ Duplicados", duplicated)
                    with col3:
                        st.metric("❌ Erros", errors)
                    
                    if imported > 0:
                        st.success(f"🎉 Importação concluída! {imported} médicos foram cadastrados.")
                        st.balloons()
                    
                    if duplicated > 0:
                        st.warning(f"⚠️ {duplicated} médicos já estavam cadastrados (CRM duplicado) e foram ignorados.")
                    
                    if errors > 0:
                        st.error(f"❌ {errors} linhas tiveram erro no processamento.")
        
        except Exception as e:
            st.error(f"❌ Erro ao processar arquivo: {str(e)}")
            st.info("Verifique se o arquivo está no formato correto.")
    
    # Opção de baixar modelo
    st.markdown("---")
    st.subheader("📥 Baixar Modelo de Importação")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gera CSV modelo
        modelo_csv = """crm,nome,especialidade,telefone,email
12345/SP,Dr. João Silva,Clínico Geral,(11) 99999-9999,joao@email.com
23456/RJ,Dra. Maria Santos,Cardiologia,(21) 98888-8888,maria@email.com
34567/MG,Dr. Pedro Costa,Ortopedia,(31) 97777-7777,pedro@email.com
45678/SP,Dra. Ana Oliveira,Pediatria,(11) 98888-7777,ana@email.com
56789/RJ,Dr. Carlos Souza,Dermatologia,(21) 97777-6666,carlos@email.com"""
        
        st.download_button(
            label="📄 Baixar Modelo CSV",
            data=modelo_csv,
            file_name="modelo_medicos.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Gera Excel modelo
        df_modelo = pd.DataFrame({
            'crm': ['12345/SP', '23456/RJ', '34567/MG', '45678/SP', '56789/RJ'],
            'nome': ['Dr. João Silva', 'Dra. Maria Santos', 'Dr. Pedro Costa', 'Dra. Ana Oliveira', 'Dr. Carlos Souza'],
            'especialidade': ['Clínico Geral', 'Cardiologia', 'Ortopedia', 'Pediatria', 'Dermatologia'],
            'telefone': ['(11) 99999-9999', '(21) 98888-8888', '(31) 97777-7777', '(11) 98888-7777', '(21) 97777-6666'],
            'email': ['joao@email.com', 'maria@email.com', 'pedro@email.com', 'ana@email.com', 'carlos@email.com']
        })
        
        # Converte para Excel em memória
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_modelo.to_excel(writer, index=False, sheet_name='Médicos')
        excel_data = output.getvalue()
        
        st.download_button(
            label="📊 Baixar Modelo Excel",
            data=excel_data,
            file_name="modelo_medicos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

def show_complete_report_import(storage):
    """Importar relatório completo de atestados (funcionários + médicos + atendimentos)"""
    
    st.header("📥 Importar Relatório Completo de Atestados")
    
    st.info("💡 Importe o relatório Excel com funcionários, médicos e atendimentos de uma só vez!")
    
    # Instruções
    with st.expander("📖 Como funciona a importação do relatório"):
        st.markdown("""
        ### Formato Esperado do Arquivo
        
        O sistema detecta automaticamente a estrutura do seu relatório Excel:
        
        **Colunas esperadas:**
        - **Coluna A**: Nome do Funcionário
        - **Coluna B**: Matrícula (MAT.)
        - **Coluna C**: Médico (com CRM no texto)
        - **Coluna D**: Local do atendimento (opcional)
        
        ### Exemplo:
        | Nome Funcionário | Matrícula | Médico | Local |
        |------------------|-----------|--------|-------|
        | RUTI MARA PORTO | 4589 | Dra:Érikada C.S.Vianna CRM 24.032 | Clínica |
        |  |  | Dr.André F.da Silva CRM 81102 | Ceam |
        | MEIRE OLIVEIRA | 11778 | Dra:Nayanne G.Marciano CRM99167 | Posto |
        
        ### O que o sistema faz automaticamente:
        1. ✅ **Extrai funcionários** únicos com nome e matrícula
        2. ✅ **Extrai médicos** únicos e identifica o CRM no texto
        3. ✅ **Registra atendimentos** vinculando funcionário + médico
        4. ✅ **Ignora duplicados** (funcionários e médicos já cadastrados)
        5. ✅ **Agrupa atendimentos** quando um funcionário tem múltiplos médicos
        
        ### Observações:
        - ⚠️ Linhas sem matrícula são consideradas atendimentos adicionais do último funcionário
        - ⚠️ O sistema tenta extrair o CRM do texto do médico automaticamente
        - ⚠️ Primeira linha com título/cabeçalho é ignorada automaticamente
        """)
    
    uploaded_file = st.file_uploader(
        "Escolha o arquivo Excel do relatório", 
        type=['xlsx', 'xls'],
        help="Formatos aceitos: Excel (.xlsx, .xls)",
        key="complete_report_upload"
    )
    
    if uploaded_file:
        try:
            # Lê o arquivo Excel
            df = pd.read_excel(uploaded_file, header=None)
            
            st.success(f"✅ Arquivo carregado: {uploaded_file.name}")
            st.write(f"**Total de linhas:** {len(df)}")
            
            # Mostra preview
            st.subheader("👀 Preview dos Dados")
            preview_df = df.copy()
            preview_df.columns = ['Nome Funcionário', 'Matrícula', 'Médico', 'Local']
            st.dataframe(preview_df.head(15), use_container_width=True)
            
            # Botão de importação
            st.markdown("---")
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col2:
                if st.button("📥 PROCESSAR E IMPORTAR TUDO", type="primary", use_container_width=True):
                    
                    with st.spinner("🔄 Processando relatório..."):
                        # Função para extrair CRM do texto
                        def extract_crm(text):
                            if pd.isna(text) or not text:
                                return None
                            
                            text = str(text).upper()
                            
                            # Padrões de CRM
                            patterns = [
                                r'CRM[\s:]*(\d+[\./\s]*\d*)',  # CRM 24.032 ou CRM24032
                                r'CRM[\s:]*(\d{4,6})',          # CRM 81102
                                r'(\d{4,6})[\/\s]*(SP|RJ|MG|BA|RS|PR|SC|GO|DF|PE|CE|PA)',  # 12345/SP
                            ]
                            
                            for pattern in patterns:
                                match = re.search(pattern, text)
                                if match:
                                    crm = match.group(1).replace('.', '').replace(' ', '')
                                    # Busca UF se tiver
                                    uf_match = re.search(r'[\/\s](SP|RJ|MG|BA|RS|PR|SC|GO|DF|PE|CE|PA)', text)
                                    if uf_match:
                                        return f"{crm}/{uf_match.group(1)}"
                                    return crm
                            
                            return None
                        
                        def extract_doctor_name(text):
                            if pd.isna(text) or not text:
                                return None
                            
                            text = str(text).strip()
                            # Remove CRM do nome
                            name = re.sub(r'CRM[\s:]*\d+[\./\s]*\d*', '', text, flags=re.IGNORECASE)
                            name = re.sub(r'\d{4,6}[\/\s]*(SP|RJ|MG|BA|RS|PR|SC|GO|DF|PE|CE|PA)', '', name)
                            name = name.strip().strip(':').strip()
                            
                            return name if name else None
                        
                        # Progresso
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Estatísticas
                        stats = {
                            'funcionarios_novos': 0,
                            'funcionarios_duplicados': 0,
                            'medicos_novos': 0,
                            'medicos_duplicados': 0,
                            'atendimentos_registrados': 0,
                            'erros': 0
                        }
                        
                        # Dicionários para cache
                        funcionarios_cache = {}  # matricula -> employee_id
                        medicos_cache = {}       # crm -> doctor_id
                        
                        # Carrega funcionários e médicos já existentes
                        for emp_id, emp_data in storage.data["employees"].items():
                            funcionarios_cache[str(emp_data["registration"])] = emp_id
                        
                        for doc_id, doc_data in storage.data["doctors"].items():
                            medicos_cache[doc_data["crm"].upper()] = doc_id
                        
                        current_employee_id = None
                        current_employee_name = None
                        
                        # Processa cada linha
                        for idx, row in df.iterrows():
                            try:
                                # Pula primeira linha se for cabeçalho
                                if idx == 0:
                                    header_text = str(row[0]).upper() if pd.notna(row[0]) else ""
                                    if 'ATESTADO' in header_text or 'MÊS' in header_text or 'MAT.' == str(row[1]):
                                        continue
                                
                                nome_func = str(row[0]).strip() if pd.notna(row[0]) else ""
                                matricula = str(row[1]).strip() if pd.notna(row[1]) else None
                                medico_texto = str(row[2]).strip() if pd.notna(row[2]) else None
                                local = str(row[3]).strip() if pd.notna(row[3]) and len(df.columns) > 3 else ""
                                
                                # Remove espaços extras do nome do funcionário
                                nome_func = ' '.join(nome_func.split())
                                
                                # Se tem matrícula, é um novo funcionário
                                if matricula and matricula.isdigit() and len(nome_func) > 3:
                                    
                                    # Verifica se já existe
                                    if matricula in funcionarios_cache:
                                        current_employee_id = funcionarios_cache[matricula]
                                        stats['funcionarios_duplicados'] += 1
                                    else:
                                        # Cadastra novo funcionário
                                        current_employee_id = storage.add_employee(matricula, nome_func, "")
                                        funcionarios_cache[matricula] = current_employee_id
                                        stats['funcionarios_novos'] += 1
                                    
                                    current_employee_name = nome_func
                                
                                # Processa médico se tiver
                                if medico_texto and len(medico_texto) > 3:
                                    crm = extract_crm(medico_texto)
                                    nome_medico = extract_doctor_name(medico_texto)
                                    
                                    if crm and nome_medico:
                                        crm_upper = crm.upper()
                                        
                                        # Verifica se médico já existe
                                        if crm_upper in medicos_cache:
                                            doctor_id = medicos_cache[crm_upper]
                                            stats['medicos_duplicados'] += 1
                                        else:
                                            # Cadastra novo médico
                                            doctor_id = storage.add_doctor(crm, nome_medico, "", "", "")
                                            medicos_cache[crm_upper] = doctor_id
                                            stats['medicos_novos'] += 1
                                        
                                        # Registra atendimento se tiver funcionário atual
                                        if current_employee_id:
                                            cert_date = datetime.date.today().isoformat()
                                            storage.add_certificate(
                                                doctor_id, 
                                                current_employee_id, 
                                                cert_date, 
                                                1,  # 1 dia de afastamento padrão
                                                f"Local: {local}" if local else ""
                                            )
                                            stats['atendimentos_registrados'] += 1
                                
                                # Atualiza progresso
                                progress = (idx + 1) / len(df)
                                progress_bar.progress(progress)
                                status_text.text(f"Processando linha {idx + 1} de {len(df)}...")
                            
                            except Exception as e:
                                stats['erros'] += 1
                                st.warning(f"⚠️ Erro na linha {idx + 1}: {str(e)}")
                        
                        progress_bar.progress(1.0)
                        status_text.empty()
                    
                    # Relatório final
                    st.markdown("---")
                    st.subheader("📊 Relatório de Importação Completa")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### 👥 Funcionários")
                        st.metric("✅ Novos Cadastrados", stats['funcionarios_novos'])
                        st.metric("⚠️ Já Existentes", stats['funcionarios_duplicados'])
                    
                    with col2:
                        st.markdown("### 👨‍⚕️ Médicos")
                        st.metric("✅ Novos Cadastrados", stats['medicos_novos'])
                        st.metric("⚠️ Já Existentes", stats['medicos_duplicados'])
                    
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("📝 Atendimentos Registrados", stats['atendimentos_registrados'])
                    with col2:
                        st.metric("❌ Erros", stats['erros'])
                    
                    if stats['atendimentos_registrados'] > 0:
                        st.success(f"""
                        🎉 **Importação concluída com sucesso!**
                        
                        - {stats['funcionarios_novos']} funcionários cadastrados
                        - {stats['medicos_novos']} médicos cadastrados
                        - {stats['atendimentos_registrados']} atendimentos registrados
                        """)
                        st.balloons()
                    
                    if stats['erros'] > 0:
                        st.warning(f"⚠️ {stats['erros']} linhas apresentaram erros no processamento.")
        
        except Exception as e:
            st.error(f"❌ Erro ao processar arquivo: {str(e)}")
            st.info("Verifique se o arquivo está no formato correto do relatório.")
    
    # Informações adicionais
    st.markdown("---")
    st.subheader("💡 Dicas")
    st.markdown("""
    - ✅ O sistema detecta automaticamente quando um funcionário tem múltiplos atendimentos
    - ✅ CRMs são extraídos automaticamente do texto (ex: "Dra:Maria CRM 12345" → "12345")
    - ✅ Funcionários e médicos duplicados são ignorados automaticamente
    - ✅ Todos os atendimentos são registrados com a data atual
    - ⚠️ Certifique-se que o arquivo tem as 4 colunas: Nome, Matrícula, Médico, Local
    """)

def show_backup_management(storage):
    """Gerenciamento de backup e exportação"""
    st.header("💾 Backup & Exportar Dados")
    
    tab1, tab2, tab3 = st.tabs(["💾 Backup", "📤 Exportar", "📊 Informações"])
    
    with tab1:
        st.subheader("Criar Backup do Sistema")
        st.write("Crie um backup completo de todos os dados (médicos, funcionários e atestados)")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Criar Backup Agora", use_container_width=True, type="primary"):
                backup_file = storage.create_backup()
                st.success(f"✅ Backup criado com sucesso!")
                st.code(backup_file)
                
                # Opção de download do backup
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = f.read()
                
                st.download_button(
                    label="📥 Baixar Backup",
                    data=backup_data,
                    file_name=f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
        
        with col2:
            st.info("💡 **Dica:** Faça backups regulares para não perder dados importantes!")
            
        # Lista de backups existentes
        st.markdown("---")
        st.subheader("📁 Backups Disponíveis")
        
        if os.path.exists(storage.backup_dir):
            backups = [f for f in os.listdir(storage.backup_dir) if f.endswith('.json')]
            backups.sort(reverse=True)
            
            if backups:
                for backup in backups[:10]:  # Mostra últimos 10
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.text(f"📄 {backup}")
                    with col2:
                        backup_path = os.path.join(storage.backup_dir, backup)
                        with open(backup_path, 'r', encoding='utf-8') as f:
                            backup_content = f.read()
                        st.download_button(
                            label="⬇️",
                            data=backup_content,
                            file_name=backup,
                            mime="application/json",
                            key=backup
                        )
            else:
                st.info("Nenhum backup criado ainda.")
    
    with tab2:
        st.subheader("Exportar Dados para Excel")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📋 Exportar Médicos**")
            if st.button("📥 Exportar Lista de Médicos", use_container_width=True):
                doctors = storage.data["doctors"]
                if doctors:
                    doctors_list = []
                    for doc_id, doc_data in doctors.items():
                        doctors_list.append({
                            'CRM': doc_data['crm'],
                            'Nome': doc_data['name'],
                            'Especialidade': doc_data['specialty'],
                            'Telefone': doc_data.get('phone', ''),
                            'Email': doc_data.get('email', ''),
                            'Total Atendimentos': doc_data['total_attendances'],
                            'Total Atestados': doc_data['total_certificates'],
                            'Último Atendimento': doc_data.get('last_attendance', '')
                        })
                    
                    df = pd.DataFrame(doctors_list)
                    
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='Médicos')
                    excel_data = output.getvalue()
                    
                    st.download_button(
                        label="📥 Baixar Excel de Médicos",
                        data=excel_data,
                        file_name=f"medicos_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.warning("Nenhum médico cadastrado.")
        
        with col2:
            st.write("**👥 Exportar Funcionários**")
            if st.button("📥 Exportar Lista de Funcionários", use_container_width=True):
                employees = storage.data["employees"]
                if employees:
                    emp_list = []
                    for emp_id, emp_data in employees.items():
                        emp_list.append({
                            'Matrícula': emp_data['registration'],
                            'Nome': emp_data['name'],
                            'Departamento': emp_data['department'],
                            'Total Atendimentos': emp_data['total_attendances'],
                            'Total Atestados': emp_data['total_certificates']
                        })
                    
                    df = pd.DataFrame(emp_list)
                    
                    from io import BytesIO
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='Funcionários')
                    excel_data = output.getvalue()
                    
                    st.download_button(
                        label="📥 Baixar Excel de Funcionários",
                        data=excel_data,
                        file_name=f"funcionarios_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.warning("Nenhum funcionário cadastrado.")
        
        st.markdown("---")
        st.write("**📝 Exportar Atestados Completo**")
        if st.button("📥 Exportar Relatório Completo de Atestados", use_container_width=True, type="primary"):
            certificates = storage.data["certificates"]
            doctors = storage.data["doctors"]
            employees = storage.data["employees"]
            
            if certificates:
                cert_list = []
                for cert_id, cert_data in certificates.items():
                    doctor = doctors.get(cert_data['doctor_id'], {})
                    employee = employees.get(cert_data['employee_id'], {})
                    
                    cert_list.append({
                        'Data do Atestado': cert_data['certificate_date'],
                        'Médico': doctor.get('name', 'Desconhecido'),
                        'CRM': doctor.get('crm', ''),
                        'Especialidade': doctor.get('specialty', ''),
                        'Funcionário': employee.get('name', 'Desconhecido'),
                        'Matrícula': employee.get('registration', ''),
                        'Departamento': employee.get('department', ''),
                        'Dias de Afastamento': cert_data['days_off'],
                        'Diagnóstico': cert_data.get('diagnosis', '')
                    })
                
                df = pd.DataFrame(cert_list)
                df = df.sort_values('Data do Atestado', ascending=False)
                
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Atestados')
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📥 Baixar Relatório Completo",
                    data=excel_data,
                    file_name=f"relatorio_atestados_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
                st.success(f"✅ Relatório com {len(cert_list)} atestados pronto para download!")
            else:
                st.warning("Nenhum atestado registrado.")
    
    with tab3:
        st.subheader("📊 Informações do Sistema")
        
        stats = storage.get_statistics()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("👨‍⚕️ Total de Médicos", stats["total_doctors"])
            st.metric("👥 Total de Funcionários", stats["total_employees"])
            st.metric("📝 Total de Atestados", stats["total_certificates"])
        
        with col2:
            st.metric("🏥 Total de Atendimentos", stats["total_attendances"])
            st.metric("📊 Média Atestados/Médico", f"{stats['certificates_per_doctor']:.1f}")
            st.metric("📊 Média Atestados/Funcionário", f"{stats['certificates_per_employee']:.1f}")
        
        st.markdown("---")
        st.write(f"**🕐 Última atualização:** {storage.data['last_update']}")
        st.write(f"**📁 Arquivo de dados:** `{storage.data_file}`")
        st.write(f"**💾 Pasta de backups:** `{storage.backup_dir}`")

if __name__ == "__main__":
    main()

