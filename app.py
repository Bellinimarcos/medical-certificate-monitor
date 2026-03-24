import streamlit as st
import pandas as pd
import json
import datetime
import os
import re
from io import BytesIO
import uuid
import google.generativeai as genai

# --- CLASSE: ANALISTA DE CIDs E RISCOS PSICOSSOCIAIS ---
class CIDAnalyst:
    def __init__(self):
        self.cids_risco = {
            'Z73.0': 'Burnout (Esgotamento Profissional)',
            'QD85': 'Burnout (CID-11)',
            'F32': 'Episódio Depressivo',
            'F33': 'Transtorno Depressivo Recorrente',
            'F34': 'Transtornos de humor persistentes',
            'F40': 'Transtornos fóbico-ansiosos',
            'F41': 'Transtornos de Ansiedade (Pânico/Generalizada)',
            'F43': 'Reações ao Stress Grave (Pós-traumático/Agudo)',
            'Z56': 'Problemas relacionados ao emprego (Geral)',
            'Z56.3': 'Ritmo de trabalho penoso',
            'Z56.6': 'Dificuldades físicas/mentais relacionadas ao trabalho',
            'Z60.5': 'Vítima de perseguição/discriminação',
            'Y07': 'Síndromes de maus tratos',
            'T74': 'Síndromes de maus tratos'
        }

    def reconhecer_cid(self, cid_input: str) -> str:
        if not cid_input or pd.isna(cid_input): return ""
        clean = str(cid_input).upper().strip().replace('.', '')
        if clean == "SEM CID" or clean == "NAN": return ""
        # Lida com CIDs múltiplos separados por barra ou mais
        clean = clean.split('/')[0].split('+')[0].strip()
        if len(clean) > 3: return f"{clean[:3]}.{clean[3:]}"
        return clean

    def analisar_risco_nr1(self, cid_formatado: str) -> dict:
        if not cid_formatado: return {"risco": False, "msg": ""}
        cid_clean = cid_formatado.replace('.', '')
        for cid_base, descricao in self.cids_risco.items():
            base_clean = cid_base.replace('.', '')
            if cid_clean.startswith(base_clean):
                return {
                    "risco": True,
                    "categoria": "RISCO PSICOSSOCIAL (NR-1)",
                    "detalhe": descricao,
                    # Sanitização de risco jurídico: Foco preventivo sem nexo causal
                    "alerta": f"⚠️ ALERTA NR-1: Este CID indica {descricao}. Recomendada avaliação multiprofissional preventiva."
                }
        return {"risco": False, "msg": "CID sem alerta imediato."}

# --- CLASSE DE ARMAZENAMENTO ---
class MedicalStorage:
    def __init__(self, data_file="data/medical_data.json", backup_dir="backups/"):
        self.data_file = data_file
        self.backup_dir = backup_dir
        self._ensure_directories()
        self.load_data()
    
    def _ensure_directories(self):
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def load_data(self):
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.data = {"doctors": {}, "employees": {}, "certificates": {}, "last_update": datetime.datetime.now().isoformat()}
            self.save_data()
    
    def save_data(self):
        self.data["last_update"] = datetime.datetime.now().isoformat()
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add_doctor(self, crm: str, name: str, specialty: str = ""):
        for doctor_id, doctor_data in self.data["doctors"].items():
            if doctor_data["crm"].lower() == crm.lower(): return doctor_id
        doctor_id = str(uuid.uuid4())
        self.data["doctors"][doctor_id] = {"crm": crm, "name": name, "specialty": specialty, "total_attendances": 0, "total_certificates": 0}
        self.save_data()
        return doctor_id

    def add_employee(self, registration: str, name: str, department: str = "", role: str = ""):
        for employee_id, employee_data in self.data["employees"].items():
            if employee_data["registration"] == registration: 
                if role and not employee_data.get("role"):
                    self.data["employees"][employee_id]["role"] = role
                    self.save_data()
                return employee_id
                
        employee_id = str(uuid.uuid4())
        self.data["employees"][employee_id] = {
            "registration": registration, 
            "name": name, 
            "department": department, 
            "role": role, 
            "total_attendances": 0, 
            "total_certificates": 0
        }
        self.save_data()
        return employee_id
    
    def add_certificate(self, doctor_id: str, employee_id: str, certificate_date: str, days_off: int = 0, diagnosis: str = "", cid: str = "", workplace: str = ""):
        certificate_id = str(uuid.uuid4())
        analyst = CIDAnalyst()
        cid_fmt = analyst.reconhecer_cid(cid)
        analise = analyst.analisar_risco_nr1(cid_fmt)
        
        self.data["certificates"][certificate_id] = {
            "doctor_id": doctor_id,
            "employee_id": employee_id,
            "certificate_date": certificate_date,
            "days_off": days_off,
            "diagnosis": diagnosis,
            "workplace": workplace,
            "cid": cid_fmt,
            "is_psychosocial_risk": analise["risco"],
            "risk_detail": analise.get("detalhe", ""),
            "created_at": datetime.datetime.now().isoformat()
        }
        
        if doctor_id in self.data["doctors"]:
            self.data["doctors"][doctor_id]["total_certificates"] += 1
        
        if employee_id in self.data["employees"]:
            self.data["employees"][employee_id]["total_certificates"] += 1
        
        self.save_data()
        return certificate_id
    
    def get_statistics(self):
        total_doctors = len(self.data["doctors"])
        total_employees = len(self.data["employees"])
        total_certificates = len(self.data["certificates"])
        total_risco_psi = sum(1 for c in self.data["certificates"].values() if c.get("is_psychosocial_risk"))
        return {"total_doctors": total_doctors, "total_employees": total_employees, "total_certificates": total_certificates, "total_risco_psi": total_risco_psi}

    def get_top_doctors_certificates(self, limit=10):
        doctors_list = []
        for doctor_id, doctor_data in self.data["doctors"].items():
            doctors_list.append({"name": doctor_data["name"], "crm": doctor_data["crm"], "total_certificates": doctor_data["total_certificates"]})
        return sorted(doctors_list, key=lambda x: x["total_certificates"], reverse=True)[:limit]
    
    def get_top_employees_certificates(self, limit=10):
        employees_list = []
        for employee_id, employee_data in self.data["employees"].items():
            employees_list.append({"name": employee_data["name"], "department": employee_data["department"], "total_certificates": employee_data["total_certificates"]})
        return sorted(employees_list, key=lambda x: x["total_certificates"], reverse=True)[:limit]

# --- CONFIGURAÇÃO VISUAL ---
def setup_streamlit_app():
    st.set_page_config(page_title="Gestão de Saúde & Riscos NR-1", page_icon="🏥", layout="wide")

# --- TELAS DO SISTEMA ---
def show_dashboard(storage):
    st.header("📊 Dashboard de Monitoramento")
    stats = storage.get_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("👨‍⚕️ Médicos", stats["total_doctors"])
    with col2: st.metric("👥 Funcionários", stats["total_employees"])
    with col3: st.metric("📝 Atestados", stats["total_certificates"])
    with col4: st.metric("⚠️ Risco NR-1", stats["total_risco_psi"], delta_color="inverse")
    
    st.markdown("---")

    st.subheader("🚨 Casos de Risco Psicossocial (Atenção Preventiva)")
    risks = []
    for cert in storage.data["certificates"].values():
        if cert.get("is_psychosocial_risk"):
            emp = storage.data["employees"].get(cert["employee_id"], {})
            risks.append({
                "Data": cert["certificate_date"],
                "Funcionário": emp.get("name", "Desconhecido"),
                "Cargo": emp.get("role", "-"),
                "CID": cert.get("cid", ""),
                "Risco": cert.get("risk_detail", "")
            })
    
    if risks:
        st.error(f"⚠️ {len(risks)} registros de risco encontrados.")
        st.dataframe(pd.DataFrame(risks).sort_values(by="Data", ascending=False), hide_index=True, use_container_width=True)
    else:
        st.success("✅ Nenhum risco detectado.")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("👨‍⚕️ 10 Médicos que mais emitem atestados")
        top_docs = storage.get_top_doctors_certificates(10)
        if top_docs:
            df = pd.DataFrame(top_docs).rename(columns={'name': 'Médico', 'crm': 'CRM', 'total_certificates': 'Qtd. Emitida'})
            st.dataframe(df, hide_index=True, use_container_width=True)
            
    with col2:
        st.subheader("👥 10 Funcionários que mais entregam atestados")
        top_emps = storage.get_top_employees_certificates(10)
        if top_emps:
            df = pd.DataFrame(top_emps).rename(columns={'name': 'Funcionário', 'department': 'Setor', 'total_certificates': 'Qtd. Entregue'})
            st.dataframe(df, hide_index=True, use_container_width=True)

def show_ai_analysis(storage):
    st.header("🤖 Análise Inteligente (PCMSO)")
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        st.warning("⚠️ Configure a chave API no secrets.toml")
        return

    st.info("A IA analisará os dados com foco nas solicitações do Gestor (Cargos e CIDs).")
    
    if st.button("🚀 Gerar Relatório Técnico"):
        with st.spinner("Analisando dados..."):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                stats = storage.get_statistics()
                riscos = {}
                cargos_afastados = {}
                
                for cert in storage.data["certificates"].values():
                    if cert.get('is_psychosocial_risk'):
                        detalhe = cert.get('risk_detail', 'Outro')
                        riscos[detalhe] = riscos.get(detalhe, 0) + 1
                        
                        emp = storage.data["employees"].get(cert['employee_id'])
                        if emp:
                            cargo = emp.get('role', 'Não Informado')
                            cargos_afastados[cargo] = cargos_afastados.get(cargo, 0) + 1

                # Prompt blindado para não gerar passivo
                prompt = f"""
                Atue como Especialista em Saúde Ocupacional. Gere um relatório técnico.
                
                DIRETRIZ CRÍTICA: É estritamente proibido mencionar nomes de departamentos, secretarias, locais de trabalho específicos ou estabelecer nexo causal direto. O foco deve ser puramente epidemiológico e na recomendação de ações preventivas globais.
                
                DADOS:
                - Total Atestados: {stats['total_certificates']}
                - Riscos Psicossociais (NR-1): {stats['total_risco_psi']}
                
                DETALHE DOS RISCOS:
                {json.dumps(riscos, ensure_ascii=False)}
                
                CARGOS MAIS AFETADOS POR RISCOS PSICOSSOCIAIS:
                {json.dumps(cargos_afastados, ensure_ascii=False)}
                
                Gere um relatório focado em:
                1. Visão geral da severidade dos CIDs.
                2. Distribuição epidemiológica por cargos afetados.
                3. Sugestões de mitigação institucionais e preventivas.
                """
                
                response = model.generate_content(prompt)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Erro na IA: {str(e)}")

def show_attendance_registration(storage):
    st.header("📝 Registrar Atendimento")
    doctors = storage.data["doctors"]
    employees = storage.data["employees"]
    
    if not doctors or not employees:
        st.warning("Cadastre médicos e funcionários primeiro.")
        return
    
    with st.form("att_form"):
        col1, col2 = st.columns(2)
        with col1:
            doc_opts = {f"{d['name']} ({d['crm']})": k for k,d in doctors.items()}
            sel_doc = st.selectbox("Médico", list(doc_opts.keys()))
            date = st.date_input("Data")
            days = st.number_input("Dias", min_value=1)
        with col2:
            emp_opts = {f"{e['name']} ({e['registration']})": k for k,e in employees.items()}
            sel_emp = st.selectbox("Funcionário", list(emp_opts.keys()))
            cid = st.text_input("CID (Ex: F32)", help="Código da doença")
            local = st.text_input("Local de Trabalho", placeholder="Ex: Escola Municipal X")
        
        diag = st.text_area("Observações / Diagnóstico")
        
        if st.form_submit_button("Registrar"):
            analyst = CIDAnalyst()
            analise = analyst.analisar_risco_nr1(analyst.reconhecer_cid(cid))
            storage.add_certificate(doc_opts[sel_doc], emp_opts[sel_emp], date.isoformat(), days, diag, cid, workplace=local)
            
            if analise["risco"]: st.warning(f"⚠️ {analise['alerta']}")
            else: st.success("Salvo com sucesso!")

def show_doctor_management(storage):
    st.header("👨‍⚕️ Gerenciar Médicos")
    with st.form("doc_form"):
        crm = st.text_input("CRM (Ex: 12345/MG)")
        name = st.text_input("Nome do Médico")
        spec = st.text_input("Especialidade")
        if st.form_submit_button("Salvar"):
            if crm and name:
                storage.add_doctor(crm, name, spec)
                st.success("Médico salvo!")

def show_employee_registration(storage):
    st.header("👥 Cadastrar Funcionário")
    with st.form("emp_form"):
        col1, col2 = st.columns(2)
        with col1:
            reg = st.text_input("Matrícula")
            name = st.text_input("Nome")
        with col2:
            dept = st.text_input("Departamento")
            role = st.text_input("Cargo")
        
        if st.form_submit_button("Salvar"):
            if reg and name:
                storage.add_employee(reg, name, dept, role)
                st.success("Funcionário salvo!")

# --- FUNÇÕES DE IMPORTAÇÃO ---
def show_data_import(storage):
    st.header("📁 Importar Cadastros (Carga Inicial)")
    st.info("Use esta tela para cadastrar listas grandes de uma só vez.")
    
    tab1, tab2 = st.tabs(["👥 Importar Funcionários", "👨‍⚕️ Importar Médicos"])
    
    with tab1: import_employees_ui(storage)
    with tab2: import_doctors_ui(storage)

def import_employees_ui(storage):
    st.subheader("Lista de Funcionários")
    uploaded_file = st.file_uploader("Solte seu Excel de Funcionários aqui", type=['csv', 'xlsx'], key="emp_up")
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            df.columns = df.columns.str.lower().str.strip()
            
            # Adicionado tratamento de acentos
            col_mat = next((c for c in df.columns if c in ['matricula', 'matrícula', 'registration', 'mat', 'id']), None)
            col_nome = next((c for c in df.columns if c in ['nome', 'name', 'funcionario', 'funcionário', 'servidor']), None)
            col_dept = next((c for c in df.columns if c in ['departamento', 'setor', 'local', 'lotacao', 'lotação']), None)
            col_cargo = next((c for c in df.columns if c in ['cargo', 'funcao', 'role', 'função']), None)
            
            if not col_mat or not col_nome:
                st.error("❌ Erro: Precisa de colunas reconhecidas para Matrícula e Nome.")
                return

            if st.button("📥 Confirmar Importação de Funcionários"):
                count = 0
                for _, row in df.iterrows():
                    mat = str(row[col_mat]).strip()
                    nome = str(row[col_nome]).strip()
                    dept = str(row[col_dept]).strip() if col_dept and pd.notna(row[col_dept]) else ""
                    cargo = str(row[col_cargo]).strip() if col_cargo and pd.notna(row[col_cargo]) else ""
                    if mat and nome and mat.lower() != "nan" and nome.lower() != "nan":
                        storage.add_employee(mat, nome, dept, role=cargo)
                        count += 1
                st.success(f"✅ Sucesso! {count} funcionários cadastrados.")
        except Exception as e: st.error(f"Erro: {e}")

def import_doctors_ui(storage):
    st.subheader("Lista de Médicos")
    uploaded_file = st.file_uploader("Solte seu Excel de Médicos aqui", type=['csv', 'xlsx'], key="doc_up")
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            df.columns = df.columns.str.lower().str.strip()
            
            col_crm = next((c for c in df.columns if c in ['crm', 'registro']), None)
            col_nome = next((c for c in df.columns if c in ['nome', 'name', 'medico', 'médico']), None)
            col_spec = next((c for c in df.columns if c in ['especialidade', 'area', 'área']), None)
            
            if not col_crm or not col_nome:
                st.error("❌ Erro: Precisa de 'CRM' e 'Nome'.")
                return

            if st.button("📥 Confirmar Importação de Médicos"):
                count = 0
                for _, row in df.iterrows():
                    crm = str(row[col_crm]).strip()
                    nome = str(row[col_nome]).strip()
                    spec = str(row[col_spec]).strip() if col_spec and pd.notna(row[col_spec]) else ""
                    if crm and nome and crm.lower() != "nan" and nome.lower() != "nan":
                        storage.add_doctor(crm, nome, spec)
                        count += 1
                st.success(f"✅ Sucesso! {count} médicos cadastrados.")
        except Exception as e: st.error(f"Erro: {e}")

def show_complete_report_import(storage):
    st.header("📥 Importar Relatório Completo")
    st.info("Colunas esperadas de forma rígida: Nome | Matrícula | Cargo | Médico | Local | CID")
    
    uploaded_file = st.file_uploader("Arquivo Excel Completo", type=['xlsx', 'xls', 'csv'])
    if uploaded_file and st.button("Processar Importação Completa"):
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, header=None)
            else:
                df = pd.read_excel(uploaded_file, header=None)
                
            count = 0
            
            # Helper seguro para limpar "nan" e dados vazios
            def safe_str(val):
                if pd.isna(val): return ""
                return str(val).strip()

            for idx, row in df.iterrows():
                # Garantir que a linha tenha ao menos 6 colunas
                if len(row) < 6: continue 
                
                nome_func = safe_str(row[0])
                mat = safe_str(row[1])
                cargo = safe_str(row[2])
                medico = safe_str(row[3])
                local = safe_str(row[4])
                cid = safe_str(row[5])

                # FILTRO CONSERVADOR: Ignora cabeçalhos sujos (ex: "RELATÓRIO...", "MAT.", ou vazios)
                if not mat or "MAT" in mat.upper() or not re.search(r'\d', mat):
                    continue
                    
                if not nome_func or nome_func.upper() == "NAN":
                    continue

                emp_id = storage.add_employee(mat, nome_func, "", role=cargo)
                
                # Extrai apenas números do CRM
                crm_match = re.search(r'(\d+)', medico)
                crm = crm_match.group(1) if crm_match else "00000"
                doc_id = storage.add_doctor(crm, medico)
                
                storage.add_certificate(doc_id, emp_id, datetime.date.today().isoformat(), 1, "", cid, workplace=local)
                count += 1
                
            st.success(f"✅ {count} registros processados e vinculados com sucesso!")
        except Exception as e:
            st.error(f"Erro na importação estrutural: {e}")

def show_backup_management(storage):
    st.header("💾 Exportar Dados (Excel)")
    if st.button("Baixar Relatório"):
        data = []
        for cert in storage.data["certificates"].values():
            emp = storage.data["employees"].get(cert["employee_id"], {})
            doc = storage.data["doctors"].get(cert["doctor_id"], {})
            
            data.append({
                "Nome Servidor": emp.get("name"),
                "Matrícula": emp.get("registration"),
                "Cargo": emp.get("role", ""),
                "Médico": doc.get("name"),
                "Local": cert.get("workplace", ""),
                "CID": cert.get("cid"),
                "Risco NR-1": "SIM" if cert.get("is_psychosocial_risk") else "NÃO"
            })
            
        df = pd.DataFrame(data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 Download Excel", output.getvalue(), file_name="relatorio_estruturado.xlsx")

# --- FUNÇÃO PRINCIPAL ---
def main():
    setup_streamlit_app()
    storage = MedicalStorage()
    
    st.sidebar.title("🏥 Menu Principal")
    
    api_key = None
    if "GEMINI_API_KEY" in st.secrets: api_key = st.secrets["GEMINI_API_KEY"]
    elif "GEMINI_API" in st.secrets: api_key = st.secrets["GEMINI_API"]
    elif os.environ.get("GEMINI_API_KEY"): api_key = os.environ.get("GEMINI_API_KEY")
    
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key
        st.sidebar.success("🔐 IA Ativada")
    else:
        st.sidebar.warning("⚠️ IA Off")
        
    page = st.sidebar.radio("Navegação", [
        "📊 Dashboard", "🤖 Análise IA", "📝 Registrar Atendimento", 
        "👨‍⚕️ Médicos", "👥 Funcionários", "📁 Importar", 
        "📥 Importar Relatório", "💾 Exportar Relatório"
    ])
    
    if page == "📊 Dashboard": show_dashboard(storage)
    elif page == "🤖 Análise IA": show_ai_analysis(storage)
    elif page == "📝 Registrar Atendimento": show_attendance_registration(storage)
    elif page == "👨‍⚕️ Médicos": show_doctor_management(storage)
    elif page == "👥 Funcionários": show_employee_registration(storage)
    elif page == "📁 Importar": show_data_import(storage)
    elif page == "📥 Importar Relatório": show_complete_report_import(storage)
    elif page == "💾 Exportar Relatório": show_backup_management(storage)

if __name__ == "__main__":
    main()
