// Деловая Россия · Пермский край — макет DAPI
(function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var BASE = window.BASE || '';

  // мобильное меню
  var burger = $('[data-burger]'), mnav = $('[data-mnav]');
  if (burger) burger.addEventListener('click', function () {
    var o = mnav.classList.toggle('open');
    burger.setAttribute('aria-expanded', o);
    document.body.style.overflow = o ? 'hidden' : '';
  });

  // окна
  function openM(id) { var m = document.getElementById(id); if (m) m.classList.add('open'); }
  $$('.modal').forEach(function (m) {
    m.addEventListener('click', function (e) { if (e.target === m || e.target.hasAttribute('data-close')) m.classList.remove('open'); });
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') $$('.modal.open').forEach(function (m) { m.classList.remove('open'); }); });
  $$('[data-pay]').forEach(function (a) { a.addEventListener('click', function (e) { e.preventDefault(); if (mnav) mnav.classList.remove('open'); document.body.style.overflow = ''; openM('pay'); }); });

  // слайдеры: стрелки листают по одной карточке, ленту можно тянуть мышью, стрелки прячутся, если всё видно
  $$('[data-slider]').forEach(function (s) {
    var t = $('.track', s);
    var unit = function () {
      var c = t.children[0], c2 = t.children[1];
      return c ? (c2 ? c2.offsetLeft - c.offsetLeft : c.offsetWidth) : t.clientWidth;
    };
    var step = function (d) {
      var max = t.scrollWidth - t.clientWidth;
      if (d > 0 && t.scrollLeft >= max - 4) t.scrollTo({ left: 0 });
      else if (d < 0 && t.scrollLeft <= 4) t.scrollTo({ left: max });
      else t.scrollBy({ left: d * unit() });
    };
    var p = $('[data-prev]', s), n = $('[data-next]', s);
    if (p) p.addEventListener('click', function () { step(-1); stop(); });
    if (n) n.addEventListener('click', function () { step(1); stop(); });
    var fit = function () { s.classList.toggle('fits', t.scrollWidth - t.clientWidth < 4); };
    fit(); window.addEventListener('resize', fit); window.addEventListener('load', fit);
    var auto = +s.getAttribute('data-auto'), tm = null;
    var stop = function () { if (tm) { clearInterval(tm); tm = null; } };
    if (auto) {
      tm = setInterval(function () { if (!s.matches(':hover')) step(1); }, auto);
    }
    // перетаскивание мышью (на телефоне лента листается пальцем сама)
    var down = false, x0 = 0, l0 = 0, moved = false;
    t.addEventListener('pointerdown', function (e) {
      if (e.pointerType !== 'mouse' || e.button !== 0) return;
      down = true; moved = false; x0 = e.clientX; l0 = t.scrollLeft; stop();
    });
    window.addEventListener('pointermove', function (e) {
      if (!down) return;
      var dx = e.clientX - x0;
      if (Math.abs(dx) > 5 && !moved) { moved = true; t.classList.add('drag'); }
      if (moved) t.scrollLeft = l0 - dx;
    });
    window.addEventListener('pointerup', function () {
      if (!down) return;
      down = false;
      if (moved) {
        t.classList.remove('drag');
        var u = unit(); t.scrollTo({ left: Math.round(t.scrollLeft / u) * u });
      }
    });
    t.addEventListener('click', function (e) { if (moved) { e.preventDefault(); e.stopPropagation(); moved = false; } }, true);
    t.addEventListener('dragstart', function (e) { e.preventDefault(); });
  });

  // главная новость: картинка + заголовок + точки
  var f = $('[data-feat]');
  if (f) {
    var ims = $$('[data-fi]', f), tx = $$('[data-ft]', f), ds = $$('[data-dot]', f), i = 0;
    var show = function (k) {
      i = (k + ims.length) % ims.length;
      [ims, tx, ds].forEach(function (a) { a.forEach(function (el, j) { el.classList.toggle('on', j === i); }); });
    };
    $('[data-fprev]', f).addEventListener('click', function () { show(i - 1); });
    $('[data-fnext]', f).addEventListener('click', function () { show(i + 1); });
    ds.forEach(function (d, j) { d.addEventListener('click', function () { show(j); }); });
  }

  // вкладки пресс-центра
  $$('[data-tabs]').forEach(function (w) {
    $$('[data-tab]', w).forEach(function (b) {
      b.addEventListener('click', function () {
        $$('[data-tab]', w).forEach(function (x) { x.classList.toggle('on', x === b); });
        $$('[data-pane]', w).forEach(function (p) { p.classList.toggle('on', p.dataset.pane === b.dataset.tab); });
      });
    });
  });

  // контакты: тема из плитки на главной (?topic=…) — выбираем и прокручиваем к форме
  var tp = $('[data-topic]'), q = location.search.match(/[?&]topic=(\w+)/);
  if (tp && q && $('option[value="' + q[1] + '"]', tp)) {
    tp.value = q[1];
    var to = location.search.match(/[?&]to=([^&]+)/), ta = $('textarea[name=msg]');
    if (to && ta) ta.value = 'Хочу предложить сотрудничество: ' + decodeURIComponent(to[1].replace(/\+/g, ' ')) + '\n\n';
    setTimeout(function () { $('#msg').scrollIntoView({ block: 'start' }); }, 50);
  }

  // лица: поиск по ФИО и алфавит
  $$('[data-pfind]').forEach(function (w) {
    var q = $('input', w), letter = '';
    var cards = $$('.person', w.parentNode);
    var apply = function () {
      var t = q.value.trim().toLowerCase();
      cards.forEach(function (c) {
        var n = (c.dataset.name || '').toLowerCase();
        var last = n.split(' ').pop();
        c.classList.toggle('hide', (t && n.indexOf(t) < 0) || (letter && last.charAt(0) !== letter.toLowerCase()));
      });
      $$('.people', w.parentNode).forEach(function (g) {
        var vis = $$('.person', g).some(function (c) { return !c.classList.contains('hide'); });
        g.classList.toggle('hide', !vis);
        var h = g.previousElementSibling;
        if (h && h.tagName === 'H2' && !h.nextElementSibling.matches('[data-pfind]')) h.classList.toggle('hide', !vis);
      });
    };
    q.addEventListener('input', apply);
    $$('[data-l]', w).forEach(function (b) {
      b.addEventListener('click', function () {
        letter = b.dataset.l;
        $$('[data-l]', w).forEach(function (x) { x.classList.toggle('on', x === b); });
        apply();
      });
    });
  });

  // вступление: 3 шага
  var j = $('[data-join]');
  if (j) {
    var agree = $('[data-agree]', j), first = $('[data-go="2"]', j);
    agree.addEventListener('change', function () { first.disabled = !agree.checked; });
    var go = function (n) {
      $$('[data-step]', j).forEach(function (s) { s.classList.toggle('on', s.dataset.step == n); });
      $$('[data-st]', j).forEach(function (s) { s.classList.toggle('on', s.dataset.st == n); s.classList.toggle('done', +s.dataset.st < +n); });
      var pk = $('input[name=pkg]:checked', j); var h = $('input[name=package]', j); if (pk && h) h.value = pk.value;
      j.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
    $$('[data-go]', j).forEach(function (b) { b.addEventListener('click', function (e) { e.preventDefault(); go(b.dataset.go); }); });
  }

  // формы: проверка и «спасибо». В макете никуда не отправляются; на проде — обработчик сайта → лид в Битрикс24.
  $$('[data-form]').forEach(function (fm) {
    var src = $('input[name=source]', fm);
    if (src) src.value = (new URLSearchParams(location.search).get('utm_source') || document.referrer || 'прямой заход') + ' → ' + location.pathname;
    fm.setAttribute('novalidate', '');
    fm.addEventListener('submit', function (e) {
      e.preventDefault();
      var bad = null;
      $$('[required]', fm).forEach(function (el) {
        var empty = el.type === 'checkbox' ? !el.checked : !el.value.trim();
        el.setAttribute('aria-invalid', empty);
        if (empty && !bad) bad = el;
      });
      if (bad) { bad.focus(); return; }
      fm.reset(); openM('thanks');
    });
  });

  // фото
  $$('[data-lb]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var m = document.createElement('div');
      m.className = 'modal open';
      m.innerHTML = '<div class="bx" style="max-width:1200px;padding:8px;background:#000"><button class="x" aria-label="Закрыть">×</button><img src="' + a.getAttribute('href') + '" alt="" style="width:100%"></div>';
      m.addEventListener('click', function () { m.remove(); });
      document.body.appendChild(m);
    });
  });

  // поиск
  var res = $('[data-results]');
  if (res) {
    var q = new URLSearchParams(location.search), qs = (q.get('q') || '').trim().toLowerCase(), from = q.get('from') || '', to = q.get('to') || '';
    var form = $('.srch'); if (form) { form.q.value = q.get('q') || ''; form.from.value = from; form.to.value = to; }
    var info = $('[data-sinfo]');
    if (!qs && !from && !to) { info.textContent = 'Введите запрос: название новости, мероприятия, проекта, фамилию.'; return; }
    fetch(BASE + '/assets/search.json').then(function (r) { return r.json(); }).then(function (idx) {
      var words = qs.split(/\s+/).filter(Boolean);
      var out = idx.filter(function (x) {
        var t = x[0].toLowerCase();
        if (!words.every(function (w) { return t.indexOf(w) > -1; })) return false;
        if (from && (!x[1] || x[1] < from)) return false;
        if (to && (!x[1] || x[1] > to)) return false;
        return true;
      }).slice(0, 100);
      info.textContent = out.length ? 'Найдено: ' + out.length + (out.length === 100 ? ' и больше' : '') : 'Ничего не найдено.';
      var esc = function (s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; };
      res.innerHTML = out.map(function (x) {
        var d = x[1] ? x[1].split('-').reverse().join('.') : '';
        return '<a class="row" style="grid-template-columns:1fr" href="' + x[2] + '"' + (x[3] ? ' target="_blank" rel="noopener"' : '') + '><div><small>' + [x[4], d].filter(Boolean).join(' · ') + '</small><b>' + esc(x[0]) + '</b></div></a>';
      }).join('');
    });
  }
})();
