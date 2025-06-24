# AssessorAI Crawler

Sistema de crawler para extração de proposições legislativas de assembleias estaduais brasileiras, desenvolvido com Scrapy e integração com Weaviate.

## 🏗️ Arquitetura do Projeto

```
assessorai_crawler/
├── assessorai_crawler/          # Código principal do Scrapy
│   ├── spiders/                 # Spiders para cada estado
│   │   ├── proposicoeslegislapi.py  # Spider base (classe pai)
│   │   ├── proposicoessp.py         # São Paulo
│   │   ├── proposicoesmg.py         # Minas Gerais
│   │   └── ...                      # Outros estados
│   ├── items.py                 # Definição dos dados estruturados
│   ├── pipelines.py             # Processamento e validação dos dados
│   ├── settings.py              # Configurações do Scrapy
│   └── utils.py                 # Funções utilitárias
├── output/                      # JSONs gerados pelos crawlers
├── importer.py                  # Script para importar dados no Weaviate
├── requirements.txt             # Dependências Python
└── .env                        # Variáveis de ambiente
```

## 🚀 Configuração do Ambiente

### 1. Instalação

```bash
# Clone o repositório
git clone <repo-url>
cd assessorai_crawler

# Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate     # Windows

# Instale as dependências
pip install -r requirements.txt
```

### 2. Configuração das Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# Weaviate Configuration
WEAVIATE_URL="your-weaviate-cluster-url"
WEAVIATE_APIKEY="your-weaviate-api-key"
WEAVIATE_CLASS="Bill"

# OpenAI Configuration (para embeddings)
OPENAI_APIKEY="your-openai-api-key"
```

## 📊 Como Funciona

### 1. Estrutura de Dados

O projeto usa o item `ProposicaoItem` definido em `items.py`:

```python
ProposicaoItem:
- title: str          # Título da proposição
- house: str          # Casa legislativa
- type: str           # Tipo (PL, PEC, etc.)
- number: int         # Número da proposição
- year: int           # Ano
- author: list        # Lista de autores
- subject: str        # Ementa/assunto
- full_text: str      # Texto completo
- url: str            # URL pública
- uuid: str           # Identificador único
- scraped_at: str     # Timestamp da coleta
```

### 2. Pipeline de Processamento

1. **ValidationPipeline**: Valida campos obrigatórios
2. **JsonWriterSinglePipeline**: Salva todos os itens em um único JSON

## 🕷️ Como Desenvolver um Novo Crawler Web

### Metodologia: Do Site à Estrutura de Dados

1. **🔍 Encontre a página da casa legislativa**
   - Identifique o site oficial (ex: `www.al[uf].gov.br`)
   - Localize a seção de "Proposições", "Projetos de Lei" ou similar

2. **📋 Encontre a página que lista os projetos**
   - Busque por páginas de listagem (ex: `/proposicoes`, `/projetos`)
   - Analise a paginação e filtros disponíveis

3. **🔗 Itere pela página, buscando links para projetos individuais**
   - Identifique os seletores CSS/XPath dos links
   - Colete metadados básicos da listagem (título, autor, data)

4. **💾 Armazene as variáveis necessárias**
   - Título da proposição
   - Tipo e número (PL, PEC, etc.)
   - Autor(es)
   - Data de apresentação
   - Ementa/assunto
   - URL pública

5. **📄 Faça download da íntegra e converta para markdown**
   - Acesse página individual do projeto
   - Extraia o texto completo (PDF, HTML, DOC)
   - Converta para markdown limpo

### Passo 1: Estrutura Básica do Spider

```python
# assessorai_crawler/spiders/proposicoes[uf].py
import scrapy
import hashlib
from datetime import datetime
from urllib.parse import urljoin
from ..items import ProposicaoItem

class Proposicoes[UF]Spider(scrapy.Spider):
    name = 'proposicoes[uf]'
    house = 'Nome da Casa Legislativa'
    uf = '[uf]'
    slug = f'proposicoes{uf}'
    allowed_domains = ['www.al[uf].gov.br']
    start_urls = ['https://www.al[uf].gov.br/proposicoes']
    
    def parse(self, response):
        """Parse da página de listagem de proposições"""
        # Extrair links para proposições individuais
        proposicao_links = response.css('selector-para-links::attr(href)').getall()
        
        for link in proposicao_links:
            full_url = urljoin(response.url, link)
            yield response.follow(full_url, self.parse_proposicao)
        
        # Paginação
        next_page = response.css('selector-proxima-pagina::attr(href)').get()
        if next_page:
            yield response.follow(next_page, self.parse)
    
    def parse_proposicao(self, response):
        """Parse da página individual da proposição"""
        item = ProposicaoItem()
        
        # Extrair dados básicos
        item['title'] = response.css('h1.titulo::text').get('').strip()
        item['house'] = self.house
        item['url'] = response.url
        
        # Extrair tipo e número do título
        title_parts = item['title'].split()
        item['type'] = title_parts[0] if title_parts else ''
        
        # Extrair número e ano (formato: "123/2024")
        if len(title_parts) > 1:
            try:
                num_year = title_parts[1].split('/')
                item['number'] = int(num_year[0])
                item['year'] = int(num_year[1])
            except (ValueError, IndexError):
                item['number'] = None
                item['year'] = None
        
        # Extrair outros campos
        item['author'] = self.extract_authors(response)
        item['subject'] = response.css('.ementa::text').get('').strip()
        item['presentation_date'] = self.extract_date(response)
        
        # Extrair texto completo
        texto_completo = self.extract_full_text(response)
        item['full_text'] = self.convert_to_markdown(texto_completo)
        item['length'] = len(item['full_text'] or '')
        
        # Metadados
        item['uuid'] = hashlib.md5(item['title'].encode('utf-8')).hexdigest()
        item['scraped_at'] = datetime.now().isoformat()
        
        yield item
    
    def extract_authors(self, response):
        """Extrai lista de autores"""
        authors_text = response.css('.autores::text').get('')
        return [a.strip() for a in authors_text.split(',') if a.strip()]
    
    def extract_date(self, response):
        """Extrai data de apresentação"""
        date_text = response.css('.data-apresentacao::text').get('')
        # Implementar parsing de data específico do site
        return date_text.strip()
    
    def extract_full_text(self, response):
        """Extrai texto completo da proposição"""
        # Método 1: Texto direto na página
        full_text = response.css('.texto-completo').get()
        if full_text:
            return full_text
        
        # Método 2: Link para PDF/DOC
        pdf_link = response.css('a[href*=".pdf"]::attr(href)').get()
        if pdf_link:
            # Fazer request para PDF e processar (ver seção de bibliotecas)
            pass
        
        return ''
    
    def convert_to_markdown(self, html_content):
        """Converte HTML para markdown limpo"""
        if not html_content:
            return ''
        
        # Usar biblioteca de conversão (ver seção de bibliotecas)
        # Exemplo com html2text
        import html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        return h.handle(html_content)
```

### Passo 2: Bibliotecas Úteis

Adicione ao `requirements.txt`:

```txt
# Parsing e extração
beautifulsoup4          # Parsing HTML avançado
lxml                    # Parser XML/HTML rápido
selectolax              # Parser HTML ultrarrápido

# Conversão de documentos
html2text               # HTML para Markdown
markdownify             # HTML para Markdown (alternativa)
pypandoc                # Conversão universal de documentos

# Processamento de PDF
PyPDF2                  # Extração de texto de PDF
pdfplumber              # PDF parsing avançado
pymupdf                 # PDF processing (fitz)

# Processamento de texto
bleach                  # Limpeza de HTML
textract                # Extração de texto de vários formatos

# Utilidades web
requests-html           # Requests com suporte a JavaScript
selenium                # Automação de browser (para SPAs)
playwright              # Alternativa moderna ao Selenium
```

### Passo 3: Pseudocódigo Detalhado

```python
def develop_new_crawler():
    """
    Fluxo completo para desenvolver crawler de nova casa legislativa
    """
    
    # FASE 1: RECONHECIMENTO
    target_site = identify_legislative_house_website()
    propositions_section = find_propositions_listing_page(target_site)
    
    # FASE 2: ANÁLISE DA ESTRUTURA
    pagination_pattern = analyze_pagination(propositions_section)
    list_item_selectors = identify_list_item_selectors(propositions_section)
    individual_page_pattern = analyze_individual_pages(propositions_section)
    
    # FASE 3: EXTRAÇÃO DE METADADOS
    for page in paginate_through_listings(propositions_section):
        for item_link in extract_proposition_links(page):
            metadata = extract_basic_info_from_listing(item_link)
            
            # FASE 4: EXTRAÇÃO DE CONTEÚDO COMPLETO
            individual_page = fetch_individual_page(item_link)
            full_content = extract_full_content(individual_page)
            
            # FASE 5: PROCESSAMENTO E LIMPEZA
            cleaned_content = clean_and_normalize_text(full_content)
            markdown_content = convert_to_markdown(cleaned_content)
            
            # FASE 6: ESTRUTURAÇÃO DE DADOS
            proposition_item = create_proposition_item(
                title=metadata['title'],
                house=target_site['house_name'],
                authors=metadata['authors'],
                date=metadata['date'],
                full_text=markdown_content,
                url=item_link
            )
            
            yield proposition_item

def extract_full_content(page_response):
    """Estratégias para extrair texto completo"""
    
    # ESTRATÉGIA 1: Texto direto na página HTML
    if has_direct_text_content(page_response):
        return extract_html_text(page_response)
    
    # ESTRATÉGIA 2: Download de PDF
    elif has_pdf_link(page_response):
        pdf_url = get_pdf_link(page_response)
        pdf_content = download_and_extract_pdf(pdf_url)
        return pdf_content
    
    # ESTRATÉGIA 3: Documento Word/DOC
    elif has_doc_link(page_response):
        doc_url = get_doc_link(page_response)
        doc_content = download_and_extract_doc(doc_url)
        return doc_content
    
    # ESTRATÉGIA 4: Conteúdo carregado via JavaScript
    elif requires_javascript(page_response):
        js_content = extract_with_selenium(page_response.url)
        return js_content
    
    return ""
```

### Passo 4: Implementações Específicas por Tipo de Conteúdo

```python
# Para sites com PDF
def extract_pdf_content(pdf_url):
    """Extrai texto de PDF usando pdfplumber"""
    import pdfplumber
    import requests
    
    response = requests.get(pdf_url)
    with pdfplumber.open(BytesIO(response.content)) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

# Para sites com JavaScript/SPA
def extract_with_selenium(url):
    """Extrai conteúdo de sites com JavaScript"""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    
    driver.get(url)
    # Aguardar carregamento
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "content"))
    )
    
    content = driver.find_element(By.CLASS_NAME, "texto-completo").text
    driver.quit()
    return content

# Para limpeza e conversão
def clean_and_convert_to_markdown(html_content):
    """Limpa HTML e converte para markdown"""
    import bleach
    import html2text
    
    # Limpar HTML malicioso/desnecessário
    clean_html = bleach.clean(
        html_content,
        tags=['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'h1', 'h2', 'h3'],
        strip=True
    )
    
    # Converter para markdown
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0  # Sem quebra de linha
    
    markdown = h.handle(clean_html)
    
    # Limpeza adicional
    markdown = re.sub(r'\n\n+', '\n\n', markdown)  # Múltiplas quebras
    markdown = markdown.strip()
    
    return markdown
```

### Passo 5: Ferramentas de Desenvolvimento e Debug

```python
# Ferramenta para análise de seletores CSS
def analyze_page_structure(url):
    """Analisa estrutura da página para identificar seletores"""
    import requests
    from bs4 import BeautifulSoup
    
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Identificar possíveis seletores para proposições
    potential_selectors = [
        'a[href*="proposicao"]',
        'a[href*="projeto"]', 
        'a[href*="pl"]',
        '.proposicao-item a',
        '.projeto-link',
        'tr td a'  # Para tabelas
    ]
    
    for selector in potential_selectors:
        elements = soup.select(selector)
        if elements:
            print(f"Selector '{selector}' encontrou {len(elements)} elementos")
            for i, elem in enumerate(elements[:3]):  # Primeiros 3
                print(f"  {i+1}: {elem.get('href')} - {elem.text.strip()}")

# Ferramenta para testar extração
def test_extraction(url, selectors_dict):
    """Testa seletores em uma página específica"""
    import requests
    from bs4 import BeautifulSoup
    
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    results = {}
    for field, selector in selectors_dict.items():
        try:
            element = soup.select_one(selector)
            results[field] = element.text.strip() if element else 'NOT FOUND'
        except Exception as e:
            results[field] = f'ERROR: {str(e)}'
    
    return results

# Exemplo de uso das ferramentas
if __name__ == "__main__":
    # Analisar estrutura da página de listagem
    analyze_page_structure("https://www.alxx.gov.br/proposicoes")
    
    # Testar extração em página individual
    test_selectors = {
        'title': 'h1.titulo',
        'authors': '.autores',
        'date': '.data-apresentacao',
        'subject': '.ementa',
        'full_text': '.texto-completo'
    }
    
    results = test_extraction(
        "https://www.alxx.gov.br/proposicao/123", 
        test_selectors
    )
    
    for field, value in results.items():
        print(f"{field}: {value}")
```

### Passo 6: Estratégias por Tipo de Site

```python
# TIPO 1: Sites estáticos simples (HTML tradicional)
class SimpleHTMLSpider(scrapy.Spider):
    """Para sites com HTML estático e estrutura simples"""
    
    def parse_static_listing(self, response):
        # Seletores diretos funcionam bem
        links = response.css('a.proposicao-link::attr(href)').getall()
        for link in links:
            yield response.follow(link, self.parse_proposicao)

# TIPO 2: Sites com paginação AJAX
class AjaxPaginationSpider(scrapy.Spider):
    """Para sites que carregam mais conteúdo via AJAX"""
    
    def parse_ajax_pagination(self, response):
        # Interceptar requests AJAX
        import json
        
        # Primeira página normal
        yield from self.parse_static_listing(response)
        
        # Páginas AJAX subsequentes
        ajax_url = "https://site.gov.br/api/proposicoes"
        for page in range(2, 100):  # Ajustar limite
            yield scrapy.Request(
                f"{ajax_url}?page={page}",
                callback=self.parse_ajax_response,
                headers={'X-Requested-With': 'XMLHttpRequest'}
            )
    
    def parse_ajax_response(self, response):
        data = json.loads(response.text)
        for item in data.get('items', []):
            yield response.follow(item['url'], self.parse_proposicao)

# TIPO 3: Sites Single Page Application (SPA)
class SPASpider(scrapy.Spider):
    """Para sites React/Vue/Angular"""
    
    def __init__(self):
        # Requer Selenium ou Playwright
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=options)
    
    def parse_spa_content(self, response):
        self.driver.get(response.url)
        
        # Aguardar carregamento
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "proposicao-item"))
        )
        
        # Extrair links após JavaScript executar
        elements = self.driver.find_elements(By.CSS_SELECTOR, "a.proposicao-link")
        for element in elements:
            url = element.get_attribute('href')
            yield scrapy.Request(url, callback=self.parse_proposicao)
    
    def closed(self, reason):
        self.driver.quit()
```

## 🏃‍♂️ Executando os Crawlers

### Executar um Spider Específico

```bash
# Executar spider de São Paulo
scrapy crawl proposicoessp

# Executar spider de Minas Gerais
scrapy crawl proposicoesmg

# Ver lista de todos os spiders
scrapy list
```

### Executar com Configurações Específicas

```bash
# Salvar em formato específico
scrapy crawl proposicoessp -o output/sp_dados.json

# Executar com log específico
scrapy crawl proposicoessp -L INFO

# Executar em modo debug
scrapy crawl proposicoessp -L DEBUG

# Limitar número de itens (para testes)
scrapy crawl proposicoessp -s CLOSESPIDER_ITEMCOUNT=10

# Configurar delay entre requests
scrapy crawl proposicoessp -s DOWNLOAD_DELAY=2
```

### Exemplos Práticos de Desenvolvimento

```bash
# 1. Criar novo spider interativamente
scrapy genspider proposicoesgo www.assembleia.go.gov.br

# 2. Testar seletores com scrapy shell
scrapy shell "https://www.assembleia.go.gov.br/proposicoes"

# 3. Debug específico de uma página
scrapy shell "https://www.assembleia.go.gov.br/proposicao/12345"

# 4. Executar com configurações de desenvolvimento
scrapy crawl proposicoesgo \
  -s DOWNLOAD_DELAY=1 \
  -s CLOSESPIDER_ITEMCOUNT=5 \
  -L DEBUG
```

### Comandos Úteis no Scrapy Shell

```python
# No scrapy shell, use estes comandos para testar:

# Testar seletores CSS
response.css('a.proposicao-link').getall()
response.css('h1.titulo::text').get()

# Testar XPath
response.xpath('//a[contains(@href, "proposicao")]/@href').getall()

# Seguir link e testar
fetch('https://site.gov.br/proposicao/123')
response.css('.texto-completo::text').get()

# Testar regex
import re
title = "PL 123/2024"
match = re.match(r'(\w+)\s+(\d+)/(\d+)', title)
if match:
    print(f"Tipo: {match.group(1)}, Número: {match.group(2)}, Ano: {match.group(3)}")
```

## 📤 Importando Dados para o Weaviate

Após executar os crawlers, use o script de importação:

```bash
# Importar dados de um estado específico
python importer.py output/proposicoessp_proposicoes.json

# Importar com configurações específicas
python importer.py output/proposicoessp_proposicoes.json --max-tokens 4000 --overlap 200
```

### Funcionalidades do Importer

- **Chunking inteligente**: Divide textos longos em chunks baseados em tokens
- **Deduplicação**: Evita importar dados duplicados usando UUIDs
- **Progress bar**: Mostra progresso da importação
- **Controle de tokens**: Configura tamanho máximo de chunks para embeddings

## 🔧 Configurações Avançadas

### Modificar Pipelines

Em `settings.py`, você pode ajustar a ordem e configuração dos pipelines:

```python
ITEM_PIPELINES = {
    "assessorai_crawler.pipelines.ValidationPipeline": 100,      # Validação
    "assessorai_crawler.pipelines.JsonWriterSinglePipeline": 300, # Escrita JSON
}
```

### Adicionar Novos Pipelines

Crie novos pipelines em `pipelines.py`:

```python
class CustomPipeline:
    def process_item(self, item, spider):
        # Sua lógica personalizada
        return item
```

### Debug e Logs

Configure logs em `settings.py`:

```python
# Nível de log
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR

# Arquivo de log
LOG_FILE = 'scrapy.log'
```

## 🧪 Testando Novos Spiders

### 1. Teste Básico

```bash
# Teste seco (sem executar)
scrapy check proposicoes[uf]

# Teste com poucos itens
scrapy crawl proposicoes[uf] -s CLOSESPIDER_ITEMCOUNT=10
```

### 2. Validação de Dados

```bash
# Verificar se JSON foi gerado
ls -la output/

# Validar estrutura do JSON
python -m json.tool output/proposicoes[uf]_proposicoes.json
```

### 3. Debug de Items

Adicione logs no seu spider:

```python
def parse(self, response):
    for item in super().parse(response):
        self.logger.info(f"Item processado: {item['title']}")
        yield item
```

## 📋 Checklist para Novo Estado

### Fase 1: Análise e Planejamento
- [ ] Identificar site oficial da casa legislativa
- [ ] Encontrar seção de proposições/projetos de lei
- [ ] Analisar estrutura da página de listagem
- [ ] Identificar sistema de paginação
- [ ] Verificar se requer JavaScript (SPA)
- [ ] Testar seletores com `scrapy shell`

### Fase 2: Desenvolvimento
- [ ] Criar arquivo `proposicoes[uf].py` no diretório `spiders/`
- [ ] Definir `name`, `house`, `uf` e configurações básicas
- [ ] Implementar `parse()` para listagem
- [ ] Implementar `parse_proposicao()` para páginas individuais
- [ ] Implementar extração de texto completo
- [ ] Implementar conversão para markdown

### Fase 3: Testes
- [ ] Testar spider com poucos items (`CLOSESPIDER_ITEMCOUNT=5`)
- [ ] Validar extração de todos os campos obrigatórios
- [ ] Verificar qualidade da conversão para markdown
- [ ] Testar paginação completa
- [ ] Verificar tratamento de erros

### Fase 4: Validação
- [ ] Executar coleta completa
- [ ] Validar JSON de saída
- [ ] Verificar URLs públicas funcionais
- [ ] Testar importação no Weaviate
- [ ] Documentar peculiaridades do estado

### Fase 5: Documentação
- [ ] Documentar seletores específicos usados
- [ ] Documentar estrutura particular do site
- [ ] Documentar problemas encontrados e soluções
- [ ] Atualizar README se necessário

## 🐛 Problemas Comuns

### Problemas de Seletores CSS/XPath

**Seletores não encontram elementos:**
```python
# ❌ Problema: Seletor muito específico
response.css('div.container > div.content > table.proposicoes > tr > td > a')

# ✅ Solução: Seletor mais genérico
response.css('a[href*="proposicao"]')
```

**Elementos carregados via JavaScript:**
```python
# ❌ Problema: Conteúdo não existe no HTML inicial
response.css('.proposicao-dinamica')  # Retorna vazio

# ✅ Solução: Usar Selenium
from selenium import webdriver
driver = webdriver.Chrome()
driver.get(response.url)
# Aguardar carregamento e extrair
```

### Problemas de Encoding

**Caracteres especiais quebrados:**
```python
# ✅ Solução: Configurar encoding correto
def parse(self, response):
    response = response.replace(encoding='utf-8')
    # ... resto do código
```

### Problemas de Rate Limiting

**Site bloqueia requests rápidos:**
```python
# ✅ Configurar delay no settings.py
DOWNLOAD_DELAY = 2  # 2 segundos entre requests
RANDOMIZE_DOWNLOAD_DELAY = 0.5  # Randomizar até 50%

# Ou no spider individual
custom_settings = {
    'DOWNLOAD_DELAY': 3,
    'CONCURRENT_REQUESTS': 1
}
```

### Problemas com PDFs

**PDF corrompido ou protegido:**
```python
def extract_pdf_safely(pdf_url):
    try:
        import pdfplumber
        response = requests.get(pdf_url)
        with pdfplumber.open(BytesIO(response.content)) as pdf:
            return "\n".join(page.extract_text() for page in pdf.pages)
    except Exception as e:
        # Fallback para OCR se necessário
        self.logger.warning(f"PDF extraction failed: {e}")
        return self.extract_pdf_with_ocr(pdf_url)
```

### Problemas de Validação

**Campos obrigatórios faltando:**
```python
# Verificar no pipeline se campos essenciais existem
def process_item(self, item, spider):
    required_fields = ['title', 'house', 'url', 'full_text']
    missing = [f for f in required_fields if not item.get(f)]
    
    if missing:
        spider.logger.warning(f"Missing fields: {missing}")
        # Decidir se descartar ou preencher com default
        for field in missing:
            item[field] = 'N/A'  # ou raise DropItem()
    
    return item
```

### Problemas de Memória

**Spider consome muita memória:**
```python
# ✅ Processar itens em lotes menores
custom_settings = {
    'CONCURRENT_REQUESTS': 1,
    'CLOSESPIDER_ITEMCOUNT': 1000,  # Parar após 1000 itens
}

# Ou usar generator para texto muito grande
def extract_large_text(self, response):
    for chunk in self.process_text_in_chunks(response):
        yield chunk
```

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/novo-estado`)
3. Teste thoroughly o novo spider
4. Commit suas mudanças (`git commit -am 'Add spider for XX state'`)
5. Push para a branch (`git push origin feature/novo-estado`)
6. Abra um Pull Request

## 📝 Notas Importantes

- **Dados sensíveis**: Nunca commite arquivos `.env` ou chaves de API
- **Rate limiting**: Respeite os limites das APIs e sites (use `DOWNLOAD_DELAY`)
- **Robots.txt**: Sempre verifique e respeite o arquivo robots.txt do site
- **User-Agent**: Configure um User-Agent identificável e respeitoso
- **Testes**: Sempre teste com poucos items antes de executar coleta completa
- **URLs públicas**: Verifique se as URLs extraídas são acessíveis publicamente  
- **Backup de dados**: Faça backup dos JSONs gerados antes de reprocessar
- **Monitoramento**: Sites podem mudar estrutura - monitore falhas regularmente
- **Legalidade**: Verifique se o crawling está em conformidade com os termos de uso
- **Performance**: Use `CONCURRENT_REQUESTS` e `DOWNLOAD_DELAY` apropriados

### Boas Práticas de Desenvolvimento

```python
# ✅ Sempre use try/catch para extração
def extract_safely(self, response, selector, default=''):
    try:
        return response.css(selector).get('').strip()
    except Exception as e:
        self.logger.warning(f"Failed to extract {selector}: {e}")
        return default

# ✅ Valide dados antes de salvar
def validate_item(self, item):
    if not item.get('title'):
        return False
    if not item.get('full_text') or len(item['full_text']) < 100:
        return False
    return True

# ✅ Use logs informativos
def parse_proposicao(self, response):
    self.logger.info(f"Processing: {response.url}")
    item = self.extract_item(response)
    
    if self.validate_item(item):
        self.logger.info(f"Extracted: {item['title']}")
        yield item
    else:
        self.logger.warning(f"Invalid item from: {response.url}")
```

## 📚 Recursos Úteis

- [Documentação do Scrapy](https://docs.scrapy.org/)
- [Weaviate Documentation](https://weaviate.io/developers/weaviate)
- [OpenAI API Documentation](https://platform.openai.com/docs)
