// Деловая Россия · Пермь — макет. Меню, оплата, фильтр участников, заявка.
(function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // мобильное меню
  var burger = $('[data-burger]'), mnav = $('[data-mnav]');
  if (burger && mnav) burger.addEventListener('click', function () {
    var open = mnav.classList.toggle('open');
    burger.setAttribute('aria-expanded', open);
    document.body.style.overflow = open ? 'hidden' : '';
  });

  // окно оплаты взноса
  var pay = $('#pay');
  $$('[data-pay]').forEach(function (a) {
    a.addEventListener('click', function (e) { e.preventDefault(); pay.classList.add('open'); });
  });
  if (pay) {
    pay.addEventListener('click', function (e) { if (e.target === pay || e.target.hasAttribute('data-close')) pay.classList.remove('open'); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') pay.classList.remove('open'); });
    if (location.hash === '#pay') pay.classList.add('open');
  }

  // участники: группы и поиск
  var people = $('[data-people]');
  if (people) {
    var grp = 'all', q = '';
    var apply = function () {
      $$('.person', people).forEach(function (c) {
        var ok = (grp === 'all' || c.dataset.grp === grp) && (!q || c.dataset.q.indexOf(q) > -1);
        c.classList.toggle('hide', !ok);
      });
    };
    $$('[data-f]').forEach(function (b) {
      b.addEventListener('click', function () {
        $$('[data-f]').forEach(function (x) { x.classList.remove('on'); });
        b.classList.add('on'); grp = b.dataset.f; apply();
      });
    });
    var inp = $('[data-q]');
    if (inp) inp.addEventListener('input', function () { q = inp.value.trim().toLowerCase(); apply(); });
  }

  // интерес из адреса: ?interest=...
  var params = new URLSearchParams(location.search);
  var interest = params.get('interest');
  $$('[data-form]').forEach(function (f) {
    if (interest && f.interest) {
      for (var i = 0; i < f.interest.options.length; i++) if (f.interest.options[i].text === interest) f.interest.selectedIndex = i;
    }
    if (f.source) f.source.value = (params.get('utm_source') || document.referrer || 'прямой заход') + ' → ' + location.pathname;
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      var bad = null;
      $$('[required]', f).forEach(function (el) {
        var empty = el.type === 'checkbox' ? !el.checked : !el.value.trim();
        el.setAttribute('aria-invalid', empty);
        el.style.borderColor = empty ? '#ef4444' : '';
        if (empty && !bad) bad = el;
      });
      if (bad) { bad.focus(); return; }
      // В макете заявка никуда не уходит. На проде: POST в обработчик сайта → лид в Битрикс24 (имя, компания, должность, телефон, интерес, источник).
      var box = f.closest('[data-lead]');
      if (box) box.classList.add('sent');
      if (window.ym) try { window.ym(0, 'reachGoal', 'lead_sent'); } catch (x) {}
    });
  });

  // просмотр фото
  $$('[data-lb]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var m = document.createElement('div');
      m.className = 'modal open';
      m.innerHTML = '<div class="box" style="max-width:1200px;padding:8px;background:#000"><button class="x" data-close aria-label="Закрыть">×</button><img src="' + a.getAttribute('href') + '" alt="" style="width:100%;border-radius:8px"></div>';
      m.addEventListener('click', function (ev) { if (ev.target === m || ev.target.hasAttribute('data-close') || ev.target.tagName === 'IMG') m.remove(); });
      document.body.appendChild(m);
    });
  });
})();
