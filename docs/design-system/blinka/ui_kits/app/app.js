// Blinka UI kit behaviors: radio groups, route selector, accordion, quiz gating.
(function () {
  function radioGroup(group, onChange) {
    var items = group.querySelectorAll('[role="radio"]');
    items.forEach(function (el) {
      el.addEventListener('click', function () {
        items.forEach(function (o) { o.setAttribute('aria-checked', String(o === el)); });
        onChange && onChange(el);
      });
    });
  }

  document.querySelectorAll('[data-radio]').forEach(function (g) { radioGroup(g, updateQuiz); });
  radioGroup(document.getElementById('funds'), function (el) {
    document.getElementById('fund-label').textContent = el.dataset.label;
  });

  var routes = document.querySelectorAll('.route');
  var out = document.getElementById('pay-out');
  var rail = document.getElementById('pay-rail');
  routes.forEach(function (r) {
    r.addEventListener('click', function () {
      routes.forEach(function (o) { o.setAttribute('aria-pressed', String(o === r)); });
      out.textContent = 'USD → ' + r.dataset.cur;
      rail.textContent = r.dataset.rail;
    });
  });

  document.querySelectorAll('.acc button').forEach(function (b) {
    b.addEventListener('click', function () {
      var item = b.parentElement;
      var open = item.classList.toggle('open');
      b.setAttribute('aria-expanded', String(open));
      b.lastElementChild.textContent = open ? '−' : '+';
    });
  });

  var btn = document.getElementById('quiz-continue');
  function updateQuiz() {
    var done = document.querySelectorAll('[data-radio] [aria-checked="true"]').length === 2;
    btn.disabled = !done;
    var vol = document.querySelector('#q-volume [aria-checked="true"]');
    var bal = document.querySelector('#q-balance [aria-checked="true"]');
    if (done) {
      btn.dataset.next = (vol.dataset.v === 'low' && bal.dataset.v === 'low') ? 'call' : 'apply';
    }
  }
  btn.addEventListener('click', function () {
    document.getElementById('quiz-result').textContent =
      btn.dataset.next === 'call' ? 'Next step: book a call with our team.' : 'Next step: open your account application.';
  });
})();
