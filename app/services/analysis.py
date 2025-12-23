
import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class BusinessAnalyzer:
    """
    Service responsible for applying business logic and generating summaries.
    Currently hardcoded for 'Economia Programada Bradesco'.
    """
    
    def analyze(self, text: str, rules: list = None) -> Dict[str, Any]:
        """
        Generates summary and topics using local NLP (Sumy + Scikit-learn).
        """
        logger.info(f"Starting AI Analysis (Business Rules). Text length: {len(text) if text else 0}")
        
        if not text or len(text) < 50:
             return {"summary": "Texto muito curto para análise.", "topics": ""}

        try:
            # Lazy imports to save startup time if not used
            import nltk
            from sumy.parsers.plaintext import PlaintextParser
            from sumy.nlp.tokenizers import Tokenizer
            from sumy.summarizers.lex_rank import LexRankSummarizer 
            from sumy.nlp.stemmers import Stemmer
            from sumy.utils import get_stop_words
            from sklearn.feature_extraction.text import TfidfVectorizer
            
            self._ensure_nltk_resources()
            
            LANGUAGE = "portuguese"
            text_lower = text.lower()
            
            # --- 1. Rule-Based Compliance Check ---
            conformidade = self._check_compliance(text_lower, rules=rules)
            
            # --- 2. Summarization ---
            summary = self._generate_summary(text, conformidade, LANGUAGE)
            
            # --- 3. Topic Extraction ---
            topics = self._extract_topics(text, LANGUAGE)
            
            return {
                "summary": summary,
                "topics": topics,
                "compliance": conformidade # Return raw compliance data too if needed later
            }

        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            return {"summary": "Erro na geração do resumo.", "topics": ""}

    def _ensure_nltk_resources(self):
        import nltk
        resources = ['tokenizers/punkt', 'tokenizers/punkt_tab', 'corpora/stopwords']
        for r in resources:
            try:
                nltk.data.find(r)
            except LookupError:
                pkg = r.split('/')[-1]
                if r == 'tokenizers/punkt_tab': pkg = 'punkt_tab'
                nltk.download(pkg, quiet=True)

    def _check_compliance(self, text_lower: str, rules: list = None) -> Dict[str, Any]:
        # Positive (Green) - Core Product Terms
        pos_indicators = [
            "economia premiável", "economia programada", "título de capitalização",
            "bradesco capitalização", "capitalização bradesco", "60 meses", "sessenta meses",
            "carência", "12 meses", "doze meses", "sorteio", "número da sorte",
            "resgate", "portal proteção", "0800", "central de atendimento",
            "não é investimento", "não tem rentabilidade garantida"
        ]
        
        # Neutral (Yellow) - Operational Awareness
        neu_indicators = [
             "débito na fatura", "débito automático", "reajuste", "ipca", 
             "renovação", "imposto de renda", "não renova", "cancelamento"
        ]
        
        # Negative (Red) - Misselling/Risk
        neg_indicators = [
            "investimento", "rendimento", "rentabilidade", "aplicação financeira", 
            "cdb", "poupança", "lucro", "juros",
            "obrigatório", "tem que fazer", "urgente", "só hoje", "cancelar o cartão",
            "pressão", "banco central"
        ]
        
        VALID_PARCELS = ["20", "30", "40", "50", "60", "70", "80", "90", "100", 
                        "110", "120", "130", "140", "150", "160", "170", "180", "190", "200"]

        # Merge with Dynamic Rules
        if rules:
            for rule in rules:
                clean_keys = [k.strip().lower() for k in rule['keywords'].split(',') if k.strip()]
                if rule['category'] == 'positive':
                     pos_indicators.extend(clean_keys)
                elif rule['category'] == 'negative': # Map 'negative' rule to Neutral/Warning (Yellow)
                     neu_indicators.extend(clean_keys)
                elif rule['category'] == 'critical': # Map 'critical' to Forbidden (Red)
                     neg_indicators.extend(clean_keys)

        conformidade = {
            "positivos": [],
            "neutros": [],
            "negativos": [],
            "valor_parcela": None,
            "cliente_aceitou": None
        }

        # Unique sets for scanning
        for i in set(pos_indicators):
            if i in text_lower: conformidade["positivos"].append(i)
        for i in set(neu_indicators):
            if i in text_lower: conformidade["neutros"].append(i)
        for i in set(neg_indicators):
            if i in text_lower: conformidade["negativos"].append(i)

        # Money
        money_matches = re.findall(r'r\$\s?(\d+(?:[.,]\d{2})?)', text_lower)
        for match in money_matches:
            val = match.replace(",", ".").replace(".", "")
            if val in VALID_PARCELS:
                conformidade["valor_parcela"] = f"R$ {val},00"
                break
        
        # Decision Logic (Last wins)
        last_aceite = -1
        last_recusa = -1
        
        aceite_patterns = ["aceito", "autorizo", "tudo bem", "confirmo", "pode sim", "fechado"]
        recusa_patterns = ["não quero", "não aceito", "não autorizo", "desisto", "cancela"]
        
        for p in aceite_patterns:
            pos = text_lower.rfind(p)
            if pos > last_aceite: last_aceite = pos
            
        for p in recusa_patterns:
            pos = text_lower.rfind(p)
            if pos > last_recusa: last_recusa = pos
            
        if last_aceite > last_recusa and last_aceite != -1:
            conformidade["cliente_aceitou"] = True
        elif last_recusa > last_aceite and last_recusa != -1:
            conformidade["cliente_aceitou"] = False
            
        return conformidade

    def _generate_summary(self, text: str, conformidade: dict, language: str) -> str:
        # Import local to scope
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.summarizers.lex_rank import LexRankSummarizer 
        from sumy.nlp.stemmers import Stemmer
        from sumy.utils import get_stop_words
        
        parser = PlaintextParser.from_string(text, Tokenizer(language))
        stemmer = Stemmer(language)
        summarizer = LexRankSummarizer(stemmer)
        summarizer.stop_words = get_stop_words(language)
        
        # Extractive Summary
        sentences = summarizer(parser.document, 3)
        
        # Build Structured Output
        summary_parts = ["📋 **RESUMO DA LIGAÇÃO - ECONOMIA PROGRAMADA**\n"]
        
        if conformidade["valor_parcela"]:
            summary_parts.append(f"💰 Parcela mencionada: {conformidade['valor_parcela']}/mês")
            
        if conformidade["cliente_aceitou"] is True:
            summary_parts.append("✅ Cliente: ACEITOU a proposta")
        elif conformidade["cliente_aceitou"] is False:
            summary_parts.append("❌ Cliente: RECUSOU a proposta")
        else:
            summary_parts.append("⚠️ Cliente: Decisão não identificada")
            
        # 3-Tier Classification Display
        if conformidade["positivos"]:
            summary_parts.append(f"🟢 **Conformidade (Bons Termos)**: {', '.join(sorted(set(conformidade['positivos'])))}")
            
        if conformidade["neutros"]:
             summary_parts.append(f"🟡 **Atenção Operacional**: {', '.join(sorted(set(conformidade['neutros'])))}")
             
        if conformidade["negativos"]:
             summary_parts.append(f"🔴 **RISCO CRÍTICO**: {', '.join(sorted(set(conformidade['negativos'])))}")
            
        summary_parts.append("\n📝 Principais pontos:")
        for s in sentences:
            summary_parts.append(f"- {str(s)}")
            
        return "\n".join(summary_parts)

    def _extract_topics(self, text: str, language: str) -> str:
        import nltk
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        pt_stopwords = nltk.corpus.stopwords.words(language)
        pt_stopwords.extend(['então', 'assim', 'aí', 'tá', 'bom', 'sim', 'não', 'senhor', 'falar'])
        
        vectorizer = TfidfVectorizer(
            stop_words=pt_stopwords, 
            max_features=15, 
            ngram_range=(1, 2)
        )
        
        try:
            vectorizer.fit_transform([text])
            names = vectorizer.get_feature_names_out()
            return ", ".join(names)
        except:
            return ""
