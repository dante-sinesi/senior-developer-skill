(function () {
  var params = new URLSearchParams(location.search);
  if (params.has('notas')) document.documentElement.classList.add('con-notas');
  if (params.has('solo')) return;
  document.documentElement.classList.add('marco');
  var base = location.href.split('#')[0].split('?')[0];
  var ui = document.createElement('div');
  ui.id = 'marco-ui';
  ui.setAttribute('data-herramienta', '');
  function el(tag, attrs, texto) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (texto) e.textContent = texto;
    return e;
  }
  var barra = el('div', { 'class': 'barra' });
  barra.appendChild(el('strong', {}, '{{titulo_visor}}'));
  [['desktop', 'Desktop'], ['mobile', 'Mobile'], ['ambas', 'Ambas']].forEach(function (p) {
    var b = el('button', { type: 'button', 'data-v': p[0] }, p[1]);
    if (p[0] === 'ambas') b.className = 'on';
    barra.appendChild(b);
  });
  var etiqueta = el('label');
  etiqueta.appendChild(el('input', { type: 'checkbox', id: 'ver-notas' }));
  etiqueta.appendChild(document.createTextNode(' Ver notas (aside.nota)'));
  barra.appendChild(etiqueta);
  ui.appendChild(barra);
  ui.appendChild(el('div', { 'class': 'vistas' }));
  document.body.appendChild(ui);
  var modo = 'ambas';
  function dibujar() {
    var vistas = ui.querySelector('.vistas');
    vistas.innerHTML = '';
    var lista = modo === 'ambas' ? [['Desktop', 1280, 820], ['Mobile', 390, 844]] :
      modo === 'desktop' ? [['Desktop', 1280, 820]] : [['Mobile', 390, 844]];
    var total = lista.reduce(function (s, v) { return s + v[1] + 24; }, 0);
    var ancho = window.innerWidth || document.documentElement.clientWidth || 1280;
    var k = Math.max(0.2, Math.min(1, (ancho - 32) / total));
    var notas = ui.querySelector('#ver-notas').checked ? '&notas=1' : '';
    lista.forEach(function (v) {
      var fig = document.createElement('figure');
      var cap = document.createElement('figcaption');
      cap.textContent = v[0] + ' · ' + v[1] + ' px';
      var marco = document.createElement('div');
      marco.className = 'marco-vista';
      marco.style.width = Math.round(v[1] * k) + 'px';
      marco.style.height = Math.round(v[2] * k) + 'px';
      var f = document.createElement('iframe');
      f.title = 'Vista ' + v[0];
      f.src = base + '?solo=1' + notas;
      f.style.width = v[1] + 'px';
      f.style.height = v[2] + 'px';
      f.style.transform = 'scale(' + k + ')';
      f.style.transformOrigin = '0 0';
      marco.appendChild(f);
      fig.appendChild(cap);
      fig.appendChild(marco);
      vistas.appendChild(fig);
    });
  }
  ui.querySelectorAll('[data-v]').forEach(function (b) {
    b.addEventListener('click', function () {
      modo = b.getAttribute('data-v');
      ui.querySelectorAll('[data-v]').forEach(function (x) { x.classList.toggle('on', x === b); });
      dibujar();
    });
  });
  ui.querySelector('#ver-notas').addEventListener('change', dibujar);
  window.addEventListener('resize', dibujar);
  dibujar();
})();
