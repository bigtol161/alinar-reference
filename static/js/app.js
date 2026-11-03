document.addEventListener('DOMContentLoaded', function () {
  var burger = document.getElementById('burger');
  if (burger) {
    burger.addEventListener('click', function () {
      document.body.classList.toggle('nav-open');
    });
  }

  document.querySelectorAll('.toast').forEach(function (t) {
    setTimeout(function () {
      t.classList.add('hide');
      setTimeout(function () { t.remove(); }, 450);
    }, 4200);
  });

  function maskPhone(input) {
    input.setAttribute('autocomplete', 'tel');
    input.addEventListener('input', function () {
      var d = input.value.replace(/\D/g, '');
      if (d.charAt(0) === '8') d = '7' + d.slice(1);
      if (d.charAt(0) === '9') d = '7' + d;
      if (d.charAt(0) !== '7') d = '7' + d;
      d = d.slice(0, 11);
      var out = '+7';
      if (d.length > 1) out += ' (' + d.slice(1, 4);
      if (d.length >= 4) out += ') ' + d.slice(4, 7);
      if (d.length >= 7) out += '-' + d.slice(7, 9);
      if (d.length >= 9) out += '-' + d.slice(9, 11);
      input.value = out;
    });
  }
  document.querySelectorAll('input[name="phone"]').forEach(maskPhone);

  var suggestInput = document.querySelector('[data-suggest]');
  if (suggestInput) {
    var box = document.getElementById('hero-suggest');
    var timer = null;
    suggestInput.addEventListener('input', function () {
      var q = suggestInput.value.trim();
      clearTimeout(timer);
      if (q.length < 2) {
        box.hidden = true;
        box.innerHTML = '';
        return;
      }
      timer = setTimeout(function () {
        fetch(suggestInput.dataset.suggest + '?q=' + encodeURIComponent(q))
          .then(function (r) { return r.json(); })
          .then(function (data) {
            box.innerHTML = (data.results || []).map(function (item) {
              return '<a class="suggest-item" href="' + item.url + '">' +
                '<span class="si-type">' + item.type + '</span>' +
                '<span class="si-main"><b>' + item.label + '</b>' +
                (item.sub ? '<small>' + item.sub + '</small>' : '') +
                '</span></a>';
            }).join('');
            box.hidden = !(data.results || []).length;
          })
          .catch(function () { box.hidden = true; });
      }, 180);
    });
    document.addEventListener('click', function (e) {
      if (!box.contains(e.target) && e.target !== suggestInput) box.hidden = true;
    });
  }

  var catalogForm = document.getElementById('catalog-form');
  if (catalogForm) {
    catalogForm.addEventListener('change', function (e) {
      var name = e.target.name;
      if (name === 'min' || name === 'max' || name === 'q') return;
      catalogForm.submit();
    });
  }

  var filtersToggle = document.getElementById('filters-toggle');
  if (filtersToggle) {
    filtersToggle.addEventListener('click', function () {
      document.getElementById('filters').classList.toggle('open');
    });
  }
});
