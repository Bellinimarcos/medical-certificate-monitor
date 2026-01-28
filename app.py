import streamlit as st
import pandas as pd
import json
import datetime
import os
import re
from io import BytesIO
import plotly.express as px
import uuid
import google.generativeai as genai

# --- CLASSE: ANALISTA DE CIDs E RISCOS PSICOSSOCIAIS ---
class CIDAnalyst:
    """
    Classe responsável por validar CIDs e identificar riscos da NR-1
    Focada em: Burnout, Assédio, Depressão e Estresse.
    """
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
            'Z60.5': 'Vítima de perseguição/discriminação (Indicativo de Assédio Moral)',
            'Y07': 'Síndromes de maus tratos (Pode indicar Assédio/Violência)',
            'T74': 'Síndromes de maus tratos (Abuso Psicológico/Sexual)'
        }

    def reconhecer_cid(self, cid_input: str) -> str:
        if not cid_input: return ""
        clean = str(cid_input).upper().strip().replace('.', '')
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
                    "alerta": f"⚠️ ALERTA NR-1: Este CID indica {descricao}. Recomendado investigar nexo causal ou assédio."
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
    
    def create_backup(self):
        backup_file = f"{self.backup_dir}backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        return backup_file

    def add_doctor(self, crm: str, name: str, specialty: str = "", phone: str = "", email: str = ""):
        for doctor_id, doctor_data in self.data["doctors"].items():
            if doctor_data["crm"].lower() == crm.lower(): return doctor_id
        doctor_id = str(uuid.uuid4())
        self.data["doctors"][doctor_id] = {"crm": crm, "name": name, "specialty": specialty, "phone": phone, "email": email, "total_attendances": 0, "total_certificates": 0, "created_at": datetime.datetime.now().isoformat(), "last_attendance": None}
        self.save_data()
        return doctor_id

    def add_employee(self, registration: str, name: str, department: str = ""):
        for employee_id, employee_data in self.data["employees"].items():
            if employee_data["registration"] == registration: return employee_id
        employee_id = str(uuid.uuid4())
        self.data["employees"][employee_id] = {"registration": registration, "name": name, "department": department, "total_attendances": 0, "total_certificates": 0, "created_at": datetime.datetime.now().isoformat()}
        self.save_data()
        return employee_id
    
    def add_certificate(self, doctor_id: str, employee_id: str, certificate_date: str, days_off: int = 0, diagnosis: str = "", cid: str = ""):
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
            "cid": cid_fmt,
            "is_psychosocial_risk": analise["risco"],
            "risk_detail": analise.get("detalhe", ""),
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
        doctors_list = []
        for doctor_id, doctor_data in self.data["doctors"].items():
            doctors_list.append({"doctor_id": doctor_id, "crm": doctor_data["crm"], "name": doctor_data["name"], "specialty": doctor_data["specialty"], "total_certificates": doctor_data["total_certificates"]})
        return sorted(doctors_list, key=lambda x: x["total_certificates"], reverse=True)[:limit]
    
    def get_top_employees_certificates(self, limit=10):
        employees_list = []
        for employee_id, employee_data in self.data["employees"].items():
            employees_list.append({"employee_id": employee_id, "registration": employee_data["registration"], "name": employee_data["name"], "department": employee_data["department"], "total_certificates": employee_data["total_certificates"]})
        return sorted(employees_list, key=lambda x: x["total_certificates"], reverse=True)[:limit]
    
    def get_statistics(self):
        total_doctors = len(self.data["doctors"])
        total_employees = len(self.data["employees"])
        total_certificates = len(self.data["certificates"])
        total_attendances = sum(doctor["total_attendances"] for doctor in self.data["doctors"].values())
        total_risco_psi = sum(1 for c in self.data["certificates"].values() if c.get("is_psychosocial_risk"))

        return {"total_doctors": total_doctors, "total_employees": total_employees, "total_certificates": total_certificates, "total_attendances": total_attendances, "total_risco_psi": total_risco_psi, "certificates_per_doctor": total_certificates / total_doctors if total_doctors > 0 else 0, "certificates_per_employee": total_certificates / total_employees if total_employees > 0 else 0}

# --- CONFIGURAÇÃO VISUAL ---
def setup_streamlit_app():
    st.set_page_config(page_title="Gestão de Saúde & Riscos NR-1", page_icon="🏥", layout="wide")
    st.markdown("""<style>.main-header { font-size: 2.5rem; color: #1f77b4; text-align: center; margin-bottom: 2rem; }.metric-card { background-color: #f0f2f6; padding: 1rem; border-radius: 10px; border-left: 4px solid #1f77b4; }</style>""", unsafe_allow_html=True)

# --- MÓDULO DE IA (VERSÃO FINAL - GEMINI 2.5 FLASH) ---
def show_ai_analysis(storage):
    st.header("🤖 Análise Inteligente e Relatório do PCMSO")
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("⚠️ ERRO: Chave da API Gemini não encontrada nas configurações do sistema.")
        st.info("Adicione sua chave no arquivo `.streamlit/secrets.toml`.")
        return

    st.info("A IA analisará seus dados de absenteísmo, focando especialmente nos riscos psicossociais (NR-1).")
    
    stats = storage.get_statistics()
    top_docs = storage.get_top_doctors_certificates(5)
    
    # Compilando dados
    dept_counts = {}
    riscos_psi_counts = {}
    certificates = storage.data["certificates"]
    employees = storage.data["employees"]
    
    for cert in certificates.values():
        emp = employees.get(cert['employee_id'])
        if emp and emp.get('department'):
            dept = emp['department']
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
        
        if cert.get('is_psychosocial_risk'):
            detalhe = cert.get('risk_detail', 'Outro')
            riscos_psi_counts[detalhe] = riscos_psi_counts.get(detalhe, 0) + 1

    if st.button("🚀 Gerar Análise Completa com IA", type="primary"):
        with st.spinner("O Gemini 2.5 Flash está analisando os dados..."):
            try:
                genai.configure(api_key=api_key)
                
                # SEU MODELO ESCOLHIDO
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                prompt = f"""
                Atue como um Especialista Sênior em Medicina e Segurança do Trabalho.
                Analise os dados abaixo e gere um relatório técnico para a diretoria e RH.
                
                DADOS GERAIS:
                - Funcionários: {stats['total_employees']}
                - Total Atestados: {stats['total_certificates']}
                - ALERTA: Casos de Risco Psicossocial (NR-1): {stats['total_risco_psi']}
                
                DETALHAMENTO DOS RISCOS PSICOSSOCIAIS ENCONTRADOS:
                {json.dumps(riscos_psi_counts, ensure_ascii=False)}
                
                DEPARTAMENTOS COM MAIS AFASTAMENTOS:
                {json.dumps(dept_counts, ensure_ascii=False)}
                
                ESPECIALIDADES MÉDICAS FREQUENTES:
                {[d['specialty'] for d in top_docs]}
                
                PEDIDO DO RELATÓRIO:
                1. **Análise de Risco:** Comente a gravidade dos riscos psicossociais encontrados (Burnout, Assédio, etc) à luz da nova NR-1.
                2. **Padrões:** Identifique se há concentração em departamentos específicos.
                3. **Plano de Ação:** Sugira 3 medidas imediatas (Ex: pesquisa de clima, canal de denúncia, palestras) para mitigar o passivo trabalhista.
                4. **Conclusão:** Tom profissional e direto.
                """
                
                response = model.generate_content(prompt)
                st.success("Análise gerada com sucesso!")
                st.markdown("### 📋 Relatório de Inteligência Artificial")
                st.markdown("---")
                st.write(response.text)
                
            except Exception as e:
                st.error(f"Erro ao conectar com Gemini: {str(e)}")


def show_dashboard(storage):
    st.header("📊 Dashboard de Monitoramento")
    stats = storage.get_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("👨‍⚕️ Médicos", stats["total_doctors"])
    with col2: st.metric("👥 Funcionários", stats["total_employees"])
    with col3: st.metric("📝 Atestados", stats["total_certificates"])
    with col4: st.metric("⚠️ Risco NR-1", stats["total_risco_psi"], delta_color="inverse")
    
    st.markdown("---")

    # 2. TABELA DE ALERTA DE RISCOS (NR-1)
    st.subheader("🚨 Casos de Risco Psicossocial (Atenção Imediata)")
    
    risks = []
    for cert in storage.data["certificates"].values():
        if cert.get("is_psychosocial_risk"):
            emp = storage.data["employees"].get(cert["employee_id"], {})
            risks.append({
                "Data": cert["certificate_date"],
                "Funcionário": emp.get("name", "Desconhecido"),
                "Departamento": emp.get("department", "-"),
                "CID": cert.get("cid", ""),
                "Risco Identificado": cert.get("risk_detail", ""),
                "Dias": cert["days_off"]
            })
    
    if risks:
        df_risks = pd.DataFrame(risks)
        df_risks = df_risks.sort_values(by="Data", ascending=False)
        st.error(f"⚠️ Foram encontrados {len(risks)} registros de doenças psicossociais.")
        st.dataframe(df_risks, hide_index=True, use_container_width=True, column_config={"Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY")})
    else:
        st.success("✅ Nenhum caso de risco psicossocial detectado até o momento.")

    st.markdown("---")

    # 3. Gráficos Normais
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("👨‍⚕️ Top Médicos")
        top_doctors = storage.get_top_doctors_certificates(5)
        if top_doctors:
            df = pd.DataFrame(top_doctors)
            st.dataframe(df[['name', 'crm', 'total_certificates']], hide_index=True, use_container_width=True)
            
    with col2:
        st.subheader("👥 Top Funcionários")
        top_emps = storage.get_top_employees_certificates(5)
        if top_emps:
            df = pd.DataFrame(top_emps)
            st.dataframe(df[['name', 'department', 'total_certificates']], hide_index=True, use_container_width=True)

def show_doctor_management(storage):
    st.header("👨‍⚕️ Gerenciamento de Médicos")
    with st.form("doctor_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            crm = st.text_input("CRM*", placeholder="Ex: 12345/SP")
            name = st.text_input("Nome*", placeholder="Dr. João Silva")
        with col2:
            specialty = st.text_input("Especialidade")
        if st.form_submit_button("Salvar"):
            if crm and name:
                storage.add_doctor(crm, name, specialty)
                st.success("Médico salvo!")

def show_employee_registration(storage):
    st.header("👥 Cadastrar Funcionário")
    with st.form("emp_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            reg = st.text_input("Matrícula*")
            name = st.text_input("Nome*")
        with col2:
            dept = st.text_input("Departamento")
        if st.form_submit_button("Salvar"):
            if reg and name:
                storage.add_employee(reg, name, dept)
                st.success("Funcionário salvo!")

def show_attendance_registration(storage):
    st.header("📝 Registrar Atendimento")
    doctors = storage.data["doctors"]
    employees = storage.data["employees"]
    cid_analyst = CIDAnalyst()

    if not doctors or not employees:
        st.warning("Cadastre médicos e funcionários primeiro.")
        return
    
    with st.form("att_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            doc_opts = {f"{d['name']} ({d['crm']})": k for k,d in doctors.items()}
            sel_doc = st.selectbox("Médico", list(doc_opts.keys()))
            date = st.date_input("Data", datetime.date.today())
            days = st.number_input("Dias", min_value=0, value=1)
        with col2:
            emp_opts = {f"{e['name']} ({e['registration']})": k for k,e in employees.items()}
            sel_emp = st.selectbox("Funcionário", list(emp_opts.keys()))
            cid_input = st.text_input("CID (Código)", placeholder="Ex: Z73.0, F32", help="Digite o CID para verificação da NR-1")
            diag = st.text_area("Descrição")
        
        cid_risco = False
        if cid_input:
            cid_fmt = cid_analyst.reconhecer_cid(cid_input)
            analise = cid_analyst.analisar_risco_nr1(cid_fmt)
            if analise["risco"]:
                st.error(f"{analise['alerta']}")
                cid_risco = True
            else:
                st.info(f"CID Formatado: {cid_fmt}")
        
        if st.form_submit_button("Registrar"):
            storage.add_certificate(doc_opts[sel_doc], emp_opts[sel_emp], date.isoformat(), days, diag, cid=cid_input)
            if cid_risco: st.warning("⚠️ Salvo com ALERTA DE RISCO NR-1!")
            else: st.success("Salvo com sucesso!")

def show_backup_management(storage):
    st.header("💾 Backup e Exportação")
    if st.button("Exportar Excel"):
        data = []
        for cert in storage.data["certificates"].values():
            doc = storage.data["doctors"].get(cert["doctor_id"], {})
            emp = storage.data["employees"].get(cert["employee_id"], {})
            data.append({
                "Data": cert["certificate_date"],
                "Funcionario": emp.get("name"),
                "CID": cert.get("cid"),
                "Risco NR-1": "SIM" if cert.get("is_psychosocial_risk") else "NÃO",
                "Detalhe Risco": cert.get("risk_detail", "")
            })
        df = pd.DataFrame(data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button("Baixar Excel", output.getvalue(), file_name="relatorio_saude.xlsx")

# --- FUNÇÕES DE IMPORTAÇÃO (QUE ESTAVAM FALTANDO) ---
def show_data_import(storage):
    st.header("📁 Importar CSV/Excel")
    import_type = st.radio("O que deseja importar?", ["👥 Funcionários", "👨‍⚕️ Médicos"], horizontal=True)
    if import_type == "👥 Funcionários":
        import_employees_ui(storage)
    else:
        import_doctors_ui(storage)

def import_employees_ui(storage):
    st.subheader("Importar Funcionários")
    uploaded_file = st.file_uploader("Arquivo CSV ou Excel", type=['csv', 'xlsx', 'xls'])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            st.write(f"Linhas encontradas: {len(df)}")
            df.columns = df.columns.str.lower().str.strip()
            matricula_col = next((c for c in df.columns if c in ['matricula', 'registration', 'mat']), None)
            nome_col = next((c for c in df.columns if c in ['nome', 'name', 'funcionario']), None)
            dept_col = next((c for c in df.columns if c in ['departamento', 'setor', 'area']), None)
            
            if not matricula_col or not nome_col:
                st.error("Erro: Arquivo precisa ter colunas 'matricula' e 'nome'")
                return

            if st.button("📥 Importar Funcionários"):
                count = 0
                for _, row in df.iterrows():
                    mat = str(row[matricula_col]).strip()
                    nome = str(row[nome_col]).strip()
                    dept = str(row[dept_col]).strip() if dept_col and pd.notna(row[dept_col]) else ""
                    if mat and nome:
                        storage.add_employee(mat, nome, dept)
                        count += 1
                st.success(f"✅ {count} funcionários processados!")
        except Exception as e: st.error(f"Erro: {e}")

def import_doctors_ui(storage):
    st.subheader("Importar Médicos")
    uploaded_file = st.file_uploader("Arquivo CSV ou Excel", type=['csv', 'xlsx', 'xls'], key="doc_up")
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            st.write(f"Linhas: {len(df)}")
            df.columns = df.columns.str.lower().str.strip()
            crm_col = next((c for c in df.columns if c in ['crm', 'registro']), None)
            nome_col = next((c for c in df.columns if c in ['nome', 'name', 'medico']), None)
            spec_col = next((c for c in df.columns if c in ['especialidade', 'specialty']), None)
            
            if not crm_col or not nome_col:
                st.error("Erro: Precisa de colunas 'crm' e 'nome'")
                return
                
            if st.button("📥 Importar Médicos"):
                count = 0
                for _, row in df.iterrows():
                    crm = str(row[crm_col]).strip()
                    nome = str(row[nome_col]).strip()
                    spec = str(row[spec_col]).strip() if spec_col and pd.notna(row[spec_col]) else ""
                    if crm and nome:
                        storage.add_doctor(crm, nome, spec)
                        count += 1
                st.success(f"✅ {count} médicos processados!")
        except Exception as e: st.error(f"Erro: {e}")

def show_complete_report_import(storage):
    st.header("📥 Importar Relatório Completo (Atestados)")
    st.info("Formato esperado: Nome Func | Matrícula | Médico (Texto) | Local | CID (Opcional)")
    
    uploaded_file = st.file_uploader("Relatório Excel", type=['xlsx', 'xls'], key="full_rep")
    
    if uploaded_file:
        if st.button("📥 PROCESSAR E IMPORTAR TUDO", type="primary"):
            try:
                df = pd.read_excel(uploaded_file, header=None)
                stats = {'func_novos':0, 'med_novos':0, 'atestados':0}
                
                funcs_cache = {d['registration']: k for k,d in storage.data["employees"].items()}
                meds_cache = {d['crm'].upper(): k for k,d in storage.data["doctors"].items()}
                
                progress = st.progress(0)
                
                for idx, row in df.iterrows():
                    if idx == 0: continue 
                    
                    nome_func = str(row[0]).strip() if pd.notna(row[0]) else ""
                    matricula = str(row[1]).strip() if pd.notna(row[1]) else None
                    medico_txt = str(row[2]).strip() if pd.notna(row[2]) else ""
                    local = str(row[3]).strip() if pd.notna(row[3]) and len(df.columns)>3 else ""
                    cid_imp = str(row[4]).strip() if pd.notna(row[4]) and len(df.columns)>4 else ""
                    
                    if not matricula or not matricula.isdigit(): continue
                    
                    # 1. Funcionario
                    emp_id = funcs_cache.get(matricula)
                    if not emp_id:
                        emp_id = storage.add_employee(matricula, nome_func, "")
                        funcs_cache[matricula] = emp_id
                        stats['func_novos'] += 1
                    
                    # 2. Médico
                    if medico_txt:
                        crm_match = re.search(r'CRM[\s:]*(\d+[\./\s]*\d*)', medico_txt.upper())
                        if crm_match:
                            crm_bruto = crm_match.group(1).replace('.','').replace(' ','')
                            uf_match = re.search(r'[\/\s](SP|RJ|MG|BA|RS|PR|SC|GO|DF)', medico_txt.upper())
                            uf = f"/{uf_match.group(1)}" if uf_match else ""
                            crm_final = f"{crm_bruto}{uf}"
                            
                            doc_id = meds_cache.get(crm_final.upper())
                            if not doc_id:
                                nome_med = re.sub(r'CRM.*', '', medico_txt, flags=re.IGNORECASE).strip()
                                doc_id = storage.add_doctor(crm_final, nome_med, "")
                                meds_cache[crm_final.upper()] = doc_id
                                stats['med_novos'] += 1
                            
                            # 3. Atestado
                            storage.add_certificate(doc_id, emp_id, datetime.date.today().isoformat(), 1, f"Local: {local}", cid=cid_imp)
                            stats['atestados'] += 1
                    
                    progress.progress((idx+1)/len(df))
                
                st.success(f"Concluído! {stats['func_novos']} func. novos, {stats['med_novos']} médicos novos, {stats['atestados']} atestados.")
                
            except Exception as e:
                st.error(f"Erro no processamento: {str(e)}")

# --- FUNÇÃO PRINCIPAL (MAIN) ---
def main():
    setup_streamlit_app()
    storage = MedicalStorage()
    
    st.sidebar.title("🏥 Menu Principal")
    
    # --- SETUP DA API KEY (BUSCA INTELIGENTE) ---
    api_key = None
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    elif "GEMINI_API" in st.secrets:
        api_key = st.secrets["GEMINI_API"]
    elif os.environ.get("GEMINI_API_KEY"):
        api_key = os.environ.get("GEMINI_API_KEY")
    elif os.environ.get("GEMINI_API"):
        api_key = os.environ.get("GEMINI_API")
        
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key
        st.sidebar.success("🔐 IA Ativada (Sistema)")
    else:
        st.sidebar.warning("⚠️ IA não configurada (Verifique secrets.toml)")
    
    st.sidebar.markdown("---")
    
    # --- MENU LATERAL ---
    page = st.sidebar.radio("Navegação:", [
        "📊 Dashboard", 
        "🤖 Análise IA (Relatórios)",
        "📝 Registrar Atendimento", 
        "👨‍⚕️ Gerenciar Médicos", 
        "👥 Cadastrar Funcionário", 
        "📁 Importar Dados",
        "📥 Importar Relatório Completo",
        "💾 Backup & Exportar"
    ])
    
    # --- ROTEAMENTO ---
    if page == "📊 Dashboard": show_dashboard(storage)
    elif page == "🤖 Análise IA (Relatórios)": show_ai_analysis(storage)
    elif page == "📝 Registrar Atendimento": show_attendance_registration(storage)
    elif page == "👨‍⚕️ Gerenciar Médicos": show_doctor_management(storage)
    elif page == "👥 Cadastrar Funcionário": show_employee_registration(storage)
    elif page == "📁 Importar Dados": show_data_import(storage)
    elif page == "📥 Importar Relatório Completo": show_complete_report_import(storage)
    elif page == "💾 Backup & Exportar": show_backup_management(storage)

if __name__ == "__main__":
    main()