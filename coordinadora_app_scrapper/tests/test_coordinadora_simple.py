from bs4 import BeautifulSoup

from ..scraper_web_coordinadora_simple import CoordinadoraSimple


def test_strategy_span_after_label():
    html = '''
    <div>
      <span class="strong-text title">Estado del paquete</span>
      <span class="strong-text title">Entregado</span>
    </div>
    '''
    soup = BeautifulSoup(html, 'html.parser')
    s = CoordinadoraSimple(base_url='https://example/')
    assert s._strategy_span_after_label(soup) == 'Entregado'


def test_strategy_div_detail():
    html = '''
    <div class="detail">
      <span class="light-text">Estado de la guía:</span>
      <span class="strong-text title">En terminal destino</span>
    </div>
    '''
    soup = BeautifulSoup(html, 'html.parser')
    s = CoordinadoraSimple(base_url='https://example/')
    assert s._strategy_div_detail(soup) == 'En terminal destino'


def test_strategy_label_next_span():
    html = '''
    <div>
      <span class="light-text">Estado de la guía:</span>
      <span class="strong-text title">En tránsito</span>
    </div>
    '''
    soup = BeautifulSoup(html, 'html.parser')
    s = CoordinadoraSimple(base_url='https://example/')
    assert s._strategy_label_next_span(soup) == 'En tránsito'
