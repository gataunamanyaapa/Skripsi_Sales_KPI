<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Gelatik Dashboard</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}" />
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
</head>
<body>

  <!-- ═══ NAVBAR ═══ -->
  <nav class="navbar">
    <div class="nav-brand">
      <img src="{{ url_for('static', filename='logo gelatik (2).png') }}" alt="Gelatik" class="nav-logo" />
    </div>
    <div class="nav-links">
      <a href="#" class="nav-link active" onclick="showSection('main',this)">Main</a>
      <a href="#" class="nav-link"        onclick="showSection('area',this)">Area</a>
    </div>
  </nav>

  <main class="main-content">

    <!-- ═══ FLASH MESSAGES ═══ -->
    {%- with messages = get_flashed_messages(with_categories=true) %}
      {%- if messages %}
      <div class="flash-container">
        {%- for category, message in messages %}
        <div class="flash flash-{{ category }}">
          <span class="flash-msg">{{ message }}</span>
          <button class="flash-close" onclick="this.parentElement.remove()">✕</button>
        </div>
        {%- endfor %}
      </div>
      {%- endif %}
    {%- endwith %}

    <!-- ══════════════════════════════════════════════════
         SECTION: MAIN
    ══════════════════════════════════════════════════ -->
    <div id="section-main">

      <!-- ═══ SUMMARY CARD ═══ -->
      <section class="card summary-card">
        <div class="watermark">
          <img src="{{ url_for('static', filename='logo gelatik (2).png') }}" alt="" />
        </div>

        <div class="summary-actions">
          <a href="/export" class="btn btn-green" onclick="btnFeedback(this,'⏳ Menyiapkan…',2000)">
            ⬇ Export Data
          </a>
          <button class="btn btn-outline" onclick="doRecluster(this)">
            🔄 Re-Cluster
          </button>
          <form action="/import" method="POST" enctype="multipart/form-data"
                class="form-inline" id="importForm">
            <label for="fileInput" class="btn btn-green">⬆ Import File</label>
            <input type="file" id="fileInput" name="file"
                   accept=".csv,.xlsx,.xls"
                   onchange="handleImport(this)" hidden />
          </form>
        </div>

        <div class="summary-body">
          <div class="donut-wrap">
            <canvas id="donutChart"></canvas>
            <div class="donut-center">
              {%- set ns = namespace(tot=0) -%}
              {%- for s in cluster_sections -%}{%- set ns.tot = ns.tot + s.count -%}{%- endfor -%}
              <span class="donut-num">{{ ns.tot }}</span>
              <span class="donut-label">Total</span>
            </div>
          </div>

          <div class="summary-right">
            <div class="legend-list">
              {%- for s in cluster_sections %}
              <div class="legend-row">
                <span class="leg-dot" style="background:{{ s.dot_color }}"></span>
                <span>{{ s.title }} = <strong>{{ s.count }}</strong></span>
              </div>
              {%- endfor %}
            </div>

            <div class="info-list">
              <div class="info-row"><span class="ik">Area</span><span class="is">=</span><span class="iv">{{ area }}</span></div>
              <div class="info-row"><span class="ik">Total Store Visit</span><span class="is">=</span><span class="iv">{{ total_store_visit | int }}</span></div>
              <div class="info-row"><span class="ik">FIFO/FEFO Compliance</span><span class="is">=</span><span class="iv">{{ fifo_avg }}%</span></div>
              <div class="info-row"><span class="ik">Price Tag Compliance</span><span class="is">=</span><span class="iv">{{ price_avg }}%</span></div>
              <div class="info-row"><span class="ik">Facing Compliance</span><span class="is">=</span><span class="iv">{{ facing_avg }}%</span></div>
              <div class="info-row">
                <span class="ik">K Optimal (K-Means)</span><span class="is">=</span>
                <span class="iv">k = {{ best_k }}&nbsp;<span class="k-auto">Auto</span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- Calinski-Harabasz dihapus -->
        <div class="eval-bar">
          <span class="eval-item"><span class="eval-label">Silhouette</span><span class="eval-val">{{ sil_score }}</span></span>
          <span class="eval-sep">|</span>
          <span class="eval-item"><span class="eval-label">Davies-Bouldin</span><span class="eval-val">{{ dbi_score }}</span></span>
        </div>
      </section>

      <!-- ═══ CLUSTER TABLES ═══ -->
      {%- for sec in cluster_sections %}
      <section class="card table-card">

        <div class="tier-header">
          <h2 class="sec-title" style="color:{{ sec.title_color }}">{{ sec.title }}</h2>
          <span class="tier-badge"
                style="background:{{ sec.dot_color }}20;color:{{ sec.title_color }};border:1.5px solid {{ sec.dot_color }}">
            {{ sec.count }} karyawan
          </span>
        </div>

        <div class="interp-row">
          <div class="interp-chip"><span class="chip-icon">📍</span><span>Visit: <b>{{ sec.avg.visit }}</b> ({{ sec.interp.visit }})</span></div>
          <div class="interp-chip"><span class="chip-icon">📦</span><span>Facing: <b>{{ sec.avg.facing }}%</b> ({{ sec.interp.facing }})</span></div>
          <div class="interp-chip"><span class="chip-icon">🔄</span><span>FIFO/FEFO: <b>{{ sec.avg.fifo }}%</b> ({{ sec.interp.fifo }})</span></div>
          <div class="interp-chip"><span class="chip-icon">🏷️</span><span>Price Tag: <b>{{ sec.avg.price_tag }}%</b> ({{ sec.interp.price_tag }})</span></div>
        </div>

        <div class="tbl-scroll">
          <table class="perf-table" id="tbl-{{ sec.cls }}">
            <thead>
              <tr>
                <th>Nama</th><th>Area</th><th>Work Rate</th>
                <th>Facing</th><th>FIFO/FEFO</th><th>Price Tag</th><th>Silhouette</th>
              </tr>
            </thead>
            <tbody>
              {%- if sec.data %}
                {%- for row in sec.data %}
                <tr data-i="{{ loop.index }}">
                  <td class="td-name">{{ row.nama }}</td>
                  <td><span class="area-tag">{{ row.area }}</span></td>
                  <td>
                    <div class="wrate">
                      <div class="wrate-track">
                        <div class="wrate-fill" style="width:{{ [row.work_rate,100]|min }}%;background:{{ sec.bar_color }}"></div>
                      </div>
                      <span class="wrate-num">{{ row.work_rate }}%</span>
                    </div>
                  </td>
                  <td>{{ row.facing }}%</td>
                  <td>{{ row.fifo }}%</td>
                  <td>{{ row.price_tag }}%</td>
                  <td>
                    <span class="sil-badge{%- if row.sil >= 0.5 %} sil-good{%- elif row.sil >= 0.25 %} sil-ok{%- else %} sil-bad{%- endif %}">
                      {{ row.sil }}
                    </span>
                  </td>
                </tr>
                {%- endfor %}
              {%- else %}
                <tr><td colspan="7" class="td-empty">Tidak ada data untuk tier ini</td></tr>
              {%- endif %}
            </tbody>
          </table>
        </div>

        {%- if sec.data | length > 5 %}
        <div class="more-wrap">
          <button class="btn-more" id="btn-{{ sec.cls }}"
                  data-cls="{{ sec.cls }}" data-total="{{ sec.data|length }}"
                  data-expanded="0" onclick="toggleRows(this)">
            Lihat semua {{ sec.data|length }} karyawan ▼
          </button>
        </div>
        <p class="row-ctr" id="ctr-{{ sec.cls }}">Menampilkan 5 dari {{ sec.data|length }} karyawan</p>
        {%- endif %}

      </section>
      {%- endfor %}

    </div><!-- /#section-main -->


    <!-- ══════════════════════════════════════════════════
         SECTION: AREA
    ══════════════════════════════════════════════════ -->
    <div id="section-area" style="display:none">

      <section class="card area-filter-card" style="overflow:visible;">
        <div class="watermark">
          <img src="{{ url_for('static', filename='logo gelatik (2).png') }}" alt="" />
        </div>

        <h2 class="area-filter-title">Filter Karyawan per Area</h2>
        <p class="area-filter-sub">Pilih area untuk melihat daftar karyawan yang ditugaskan beserta tier performanya.</p>

        <!-- Search + dropdown -->
        <div class="area-search-wrap">
          <div class="area-search-box">
            <span class="area-search-icon">🔍</span>
            <input type="text" id="areaSearchInput"
                   class="area-search-input"
                   placeholder="Cari atau pilih area…"
                   oninput="filterAreaDropdown(this.value)"
                   onfocus="openAreaDropdown()"
                   autocomplete="off" />
            <button class="area-search-clear" id="areaSearchClear"
                    onclick="clearAreaSearch()" style="display:none">✕</button>
          </div>
          <div class="area-dropdown" id="areaDropdown">
            <!-- opsi diisi JS dari data Jinja -->
          </div>
        </div>

        <!-- Chip area terpilih -->
        <div class="area-chips" id="areaChips" style="display:none">
          <span class="area-chip-label">Area dipilih:</span>
          <span class="area-chip-val" id="areaChipText"></span>
          <button class="area-chip-clear" onclick="clearAreaSearch()">✕ Reset</button>
        </div>

        <!-- Chart karyawan per tier untuk area terpilih -->
        <div id="areaChartWrap" style="display:none; margin-top:28px;">
          <h3 class="area-chart-title">Distribusi Karyawan per Tier</h3>
          <div class="area-chart-row">
            <div class="area-chart-box">
              <canvas id="areaBarChart" height="220"></canvas>
            </div>
            <div class="area-chart-box">
              <canvas id="areaDonutChart" height="220"></canvas>
            </div>
          </div>
        </div>
      </section>

      <!-- Chart area -->
      <section class="card area-chart-card" id="areaChartCard" style="display:none">
        <h3 class="area-chart-title">Distribusi Karyawan — <span id="areaChartLabel"></span></h3>
        <div class="area-chart-wrap">
          <canvas id="areaBarChart" height="90"></canvas>
        </div>
        <div class="area-chart-stats" id="areaChartStats"></div>
      </section>

      <!-- Hasil filter: kartu per tier yang hanya tampil row sesuai area -->
      <div id="areaResults">
        {%- for sec in cluster_sections %}
        <section class="card table-card area-result-section"
                 id="area-sec-{{ sec.cls }}" style="display:none"
                 data-tier="{{ sec.cls }}">

          <div class="tier-header">
            <h2 class="sec-title" style="color:{{ sec.title_color }}">{{ sec.title }}</h2>
            <span class="tier-badge area-result-badge"
                  id="area-badge-{{ sec.cls }}"
                  style="background:{{ sec.dot_color }}20;color:{{ sec.title_color }};border:1.5px solid {{ sec.dot_color }}">
            </span>
          </div>

          <div class="tbl-scroll">
            <table class="perf-table" id="area-tbl-{{ sec.cls }}">
              <thead>
                <tr>
                  <th>Nama</th><th>Area</th><th>Region</th><th>Work Rate</th>
                  <th>Facing</th><th>FIFO/FEFO</th><th>Price Tag</th><th>Silhouette</th>
                </tr>
              </thead>
              <tbody id="area-tbody-{{ sec.cls }}">
                <!-- diisi JS -->
              </tbody>
            </table>
          </div>
        </section>
        {%- endfor %}

        <!-- Placeholder sebelum area dipilih -->
        <div class="area-placeholder" id="areaPlaceholder">
          <div class="area-placeholder-inner">
            <span class="area-placeholder-icon">🗺️</span>
            <p>Pilih area untuk menampilkan karyawan</p>
          </div>
        </div>

        <!-- Kosong -->
        <div class="area-empty" id="areaEmpty" style="display:none">
          <span>Tidak ada karyawan ditemukan untuk area ini.</span>
        </div>
      </div>

    </div><!-- /#section-area -->

  </main>

  <!-- ═══ DATA KARYAWAN (embedded JSON untuk filter area) ═══ -->
  <script>
    const ALL_EMPLOYEES = [
      {%- for sec in cluster_sections %}
        {%- for row in sec.data %}
        {
          tier      : {{ sec.cls       | tojson }},
          tierTitle : {{ sec.title     | tojson }},
          titleColor: {{ sec.title_color | tojson }},
          barColor  : {{ sec.bar_color | tojson }},
          dotColor  : {{ sec.dot_color | tojson }},
          nama      : {{ row.nama      | tojson }},
          area      : {{ row.area      | tojson }},
          region    : {{ row.region    | tojson }},
          work_rate : {{ row.work_rate }},
          facing    : {{ row.facing }},
          fifo      : {{ row.fifo }},
          price_tag : {{ row.price_tag }},
          sil       : {{ row.sil }},
        },
        {%- endfor %}
      {%- endfor %}
    ];

    /* Lookup tables — diisi dari data di atas */
    const ALL_AREAS   = [...new Set(ALL_EMPLOYEES.map(e => e.area))]
                          .filter(a => a && a !== '-').sort();
    const TIER_COLORS = {};   // barColor per tier
    const TIER_DOT    = {};   // dotColor per tier
    const TIER_TITLES = {};   // tierTitle per tier
    const TIER_ORDER  = [];   // urutan tier sesuai cluster_sections

    ALL_EMPLOYEES.forEach(e => {
      if (!TIER_COLORS[e.tier]) {
        TIER_COLORS[e.tier] = e.barColor;
        TIER_DOT[e.tier]    = e.dotColor;
        TIER_TITLES[e.tier] = e.tierTitle;
        TIER_ORDER.push(e.tier);
      }
    });
    // deduplicate TIER_ORDER
    const _seen = new Set();
    for (let i = TIER_ORDER.length - 1; i >= 0; i--) {
      if (_seen.has(TIER_ORDER[i])) { TIER_ORDER.splice(i,1); }
      else { _seen.add(TIER_ORDER[i]); }
    }
  </script>

  <script>
    /* ═══════════════════════════════════════════════════
       NAVBAR — section switcher
    ═══════════════════════════════════════════════════ */
    function showSection(name, linkEl) {
      document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
      if (linkEl) linkEl.classList.add('active');
      document.getElementById('section-main').style.display = name === 'main' ? '' : 'none';
      document.getElementById('section-area').style.display = name === 'area' ? '' : 'none';
      if (name === 'area') buildAreaDropdown();
    }

    /* ═══════════════════════════════════════════════════
       AREA DROPDOWN
    ═══════════════════════════════════════════════════ */
    let areaDropdownBuilt = false;

    function buildAreaDropdown() {
      if (areaDropdownBuilt) return;
      areaDropdownBuilt = true;
      const dd = document.getElementById('areaDropdown');
      dd.innerHTML = ALL_AREAS.map(a =>
        `<div class="area-dd-item" onclick="selectArea(${JSON.stringify(a)})">${a}</div>`
      ).join('');
    }

    function openAreaDropdown() {
      buildAreaDropdown();
      document.getElementById('areaDropdown').classList.add('open');
    }

    function filterAreaDropdown(val) {
      const dd = document.getElementById('areaDropdown');
      dd.classList.add('open');
      const q = val.trim().toLowerCase();
      dd.querySelectorAll('.area-dd-item').forEach(item => {
        item.style.display = item.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
      document.getElementById('areaSearchClear').style.display = val ? '' : 'none';
    }

    let areaBarChartInstance = null;

    function selectArea(area) {
      document.getElementById('areaSearchInput').value = area;
      document.getElementById('areaDropdown').classList.remove('open');
      document.getElementById('areaSearchClear').style.display = '';

      /* tampilkan chip */
      const chips = document.getElementById('areaChips');
      chips.style.display = '';
      document.getElementById('areaChipText').textContent = area;

      renderAreaResults(area);
    }

    function clearAreaSearch() {
      document.getElementById('areaSearchInput').value = '';
      document.getElementById('areaSearchClear').style.display = 'none';
      document.getElementById('areaChips').style.display = 'none';
      document.getElementById('areaDropdown').classList.remove('open');
      document.getElementById('areaChartWrap').style.display = 'none';
      /* reset hasil */
      document.querySelectorAll('.area-result-section').forEach(s => s.style.display = 'none');
      document.getElementById('areaPlaceholder').style.display = '';
      document.getElementById('areaEmpty').style.display = 'none';
      if (_areaBarChart)   { _areaBarChart.destroy();   _areaBarChart   = null; }
      if (_areaDonutChart) { _areaDonutChart.destroy();  _areaDonutChart = null; }
    }

    /* Tutup dropdown klik di luar */
    document.addEventListener('click', e => {
      if (!e.target.closest('.area-search-wrap')) {
        document.getElementById('areaDropdown')?.classList.remove('open');
      }
    });

    /* ═══════════════════════════════════════════════════
       RENDER HASIL FILTER AREA
    ═══════════════════════════════════════════════════ */
    function silClass(v) {
      return v >= 0.5 ? 'sil-good' : v >= 0.25 ? 'sil-ok' : 'sil-bad';
    }

    /* Chart instances — destroy sebelum buat baru */
    let _areaBarChart   = null;
    let _areaDonutChart = null;

    function renderAreaResults(area) {
      const filtered = ALL_EMPLOYEES.filter(e =>
        e.area.toLowerCase() === area.toLowerCase()
      );

      document.querySelectorAll('.area-result-section').forEach(s => s.style.display = 'none');
      document.getElementById('areaPlaceholder').style.display = 'none';
      document.getElementById('areaEmpty').style.display = 'none';
      document.getElementById('areaChartCard').style.display = 'none';
      if (areaBarChartInstance) { areaBarChartInstance.destroy(); areaBarChartInstance = null; }

      if (!filtered.length) {
        document.getElementById('areaEmpty').style.display = '';
        return;
      }

      const byTier = {};
      filtered.forEach(e => {
        if (!byTier[e.tier]) byTier[e.tier] = [];
        byTier[e.tier].push(e);
      });

      /* ── Chart ── */
      document.getElementById('areaChartLabel').textContent = area;
      document.getElementById('areaChartCard').style.display = '';

      const tiersPresent = TIER_ORDER.filter(t => byTier[t]);
      const chartLabels  = tiersPresent.map(t => TIER_TITLES[t] || t);
      const chartColors  = tiersPresent.map(t => TIER_DOT[t] || '#ccc');

      const dataCount    = tiersPresent.map(t => byTier[t].length);
      const avg = (arr, key) => +(arr.reduce((s,r)=>s+r[key],0)/arr.length).toFixed(1);
      const dataWorkRate = tiersPresent.map(t => avg(byTier[t],'work_rate'));
      const dataFacing   = tiersPresent.map(t => avg(byTier[t],'facing'));
      const dataFifo     = tiersPresent.map(t => avg(byTier[t],'fifo'));
      const dataPriceTag = tiersPresent.map(t => avg(byTier[t],'price_tag'));

      const ctx = document.getElementById('areaBarChart').getContext('2d');
      areaBarChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: chartLabels,
          datasets: [
            { label:'Jumlah Karyawan', data:dataCount,
              backgroundColor:chartColors.map(x=>x+'BB'), borderColor:chartColors,
              borderWidth:2, borderRadius:8, yAxisID:'yCount' },
            { label:'Avg Work Rate (%)', data:dataWorkRate, type:'line',
              borderColor:'#6366f1', pointBackgroundColor:'#6366f1',
              tension:0.35, fill:false, pointRadius:5, yAxisID:'yPct' },
            { label:'Avg Facing (%)', data:dataFacing, type:'line',
              borderColor:'#f97316', pointBackgroundColor:'#f97316',
              tension:0.35, fill:false, pointRadius:5, yAxisID:'yPct' },
            { label:'Avg FIFO/FEFO (%)', data:dataFifo, type:'line',
              borderColor:'#22c55e', pointBackgroundColor:'#22c55e',
              tension:0.35, fill:false, pointRadius:5, yAxisID:'yPct' },
            { label:'Avg Price Tag (%)', data:dataPriceTag, type:'line',
              borderColor:'#E91E8C', pointBackgroundColor:'#E91E8C',
              tension:0.35, fill:false, pointRadius:5, yAxisID:'yPct' },
          ]
        },
        options:{
          responsive:true,
          interaction:{mode:'index',intersect:false},
          plugins:{
            legend:{position:'bottom',
              labels:{font:{family:"'Plus Jakarta Sans',sans-serif",size:11},padding:16,usePointStyle:true}},
            tooltip:{callbacks:{label:function(ctx){
              const v=ctx.parsed.y;
              return ' '+ctx.dataset.label+': '+(ctx.datasetIndex===0?v+' orang':v+'%');
            }}}
          },
          scales:{
            yCount:{type:'linear',position:'left',
              title:{display:true,text:'Jumlah Karyawan',font:{size:11}},
              ticks:{stepSize:1},grid:{color:'#f0e4ec'}},
            yPct:{type:'linear',position:'right',
              title:{display:true,text:'KPI (%)',font:{size:11}},
              ticks:{callback:function(v){return v+'%';}},
              grid:{drawOnChartArea:false}},
            x:{grid:{display:false}}
          }
        }
      });

      /* Stats pills */
      document.getElementById('areaChartStats').innerHTML = tiersPresent.map(function(t,i){
        return '<div class="area-stat-pill" style="border-color:'+chartColors[i]+'40;background:'+chartColors[i]+'12">'+
          '<span class="area-stat-dot" style="background:'+chartColors[i]+'"></span>'+
          '<span class="area-stat-tier">'+chartLabels[i]+'</span>'+
          '<strong>'+dataCount[i]+' karyawan</strong>'+
          '<span class="area-stat-sep">·</span>'+
          '<span>WR '+dataWorkRate[i]+'%</span>'+
          '<span class="area-stat-sep">·</span>'+
          '<span>FIFO '+dataFifo[i]+'%</span>'+
          '<span class="area-stat-sep">·</span>'+
          '<span>PT '+dataPriceTag[i]+'%</span>'+
          '</div>';
      }).join('');

      /* ── Tabel per tier ── */
      Object.entries(byTier).forEach(function(entry){
        var tier = entry[0], rows = entry[1];
        var sec   = document.getElementById('area-sec-'+tier);
        var tbody = document.getElementById('area-tbody-'+tier);
        var badge = document.getElementById('area-badge-'+tier);
        if (!sec || !tbody) return;
        badge.textContent = rows.length + ' karyawan';
        tbody.innerHTML = rows.map(function(r){
          return '<tr>'+
            '<td class="td-name">'+r.nama+'</td>'+
            '<td><span class="area-tag">'+r.area+'</span></td>'+
            '<td><span class="region-tag">'+r.region+'</span></td>'+
            '<td><div class="wrate">'+
              '<div class="wrate-track">'+
                '<div class="wrate-fill" style="width:'+Math.min(r.work_rate,100)+'%;background:'+TIER_COLORS[tier]+'"></div>'+
              '</div>'+
              '<span class="wrate-num">'+r.work_rate+'%</span>'+
            '</div></td>'+
            '<td>'+r.facing+'%</td>'+
            '<td>'+r.fifo+'%</td>'+
            '<td>'+r.price_tag+'%</td>'+
            '<td><span class="sil-badge '+silClass(r.sil)+'">'+r.sil+'</span></td>'+
          '</tr>';
        }).join('');
        sec.style.display = '';
      });
    }

    function renderAreaCharts(byTier, allRows) {
      document.getElementById('areaChartWrap').style.display = '';

      /* Susun data per tier — urut sesuai TIER_ORDER dari Flask */
      const tierOrder  = Object.keys(TIER_COLORS);
      const labels     = [];
      const counts     = [];
      const colors     = [];
      const dotColors  = [];

      /* Ambil semua tier yang muncul, urut sesuai tierOrder */
      const tiersInArea = tierOrder.filter(t => byTier[t]);
      /* Juga tambahkan tier dari byTier yang tidak ada di tierOrder */
      Object.keys(byTier).forEach(t => { if (!tiersInArea.includes(t)) tiersInArea.push(t); });

      tiersInArea.forEach(tier => {
        const rows = byTier[tier] || [];
        const emp  = allRows.find(e => e.tier === tier);
        labels.push(emp ? emp.tierTitle : tier);
        counts.push(rows.length);
        colors.push(TIER_COLORS[tier] || '#9ca3af');
        dotColors.push(TIER_COLORS[tier] || '#9ca3af');
      });

      /* KPI rata-rata */
      const avgFacing   = +(allRows.reduce((s,e)=>s+e.facing,0)   / allRows.length).toFixed(1);
      const avgFifo     = +(allRows.reduce((s,e)=>s+e.fifo,0)     / allRows.length).toFixed(1);
      const avgPriceTag = +(allRows.reduce((s,e)=>s+e.price_tag,0)/ allRows.length).toFixed(1);
      const avgWorkRate = +(allRows.reduce((s,e)=>s+e.work_rate,0) / allRows.length).toFixed(1);

      /* ── Bar chart: jumlah karyawan per tier ── */
      if (_areaBarChart) _areaBarChart.destroy();
      _areaBarChart = new Chart(document.getElementById('areaBarChart'), {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            label: 'Jumlah Karyawan',
            data: counts,
            backgroundColor: colors.map(c => c + 'cc'),
            borderColor: colors,
            borderWidth: 2,
            borderRadius: 8,
            borderSkipped: false,
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: c => ` ${c.parsed.y} karyawan` } },
            title: {
              display: true,
              text: 'Jumlah Karyawan per Tier',
              font: { size: 13, weight: '600', family: "'Plus Jakarta Sans', sans-serif" },
              color: '#1a1a2e', padding: { bottom: 12 }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { stepSize: 1, font: { size: 11 } },
              grid: { color: '#f0f0f0' }
            },
            x: { ticks: { font: { size: 11 } }, grid: { display: false } }
          }
        }
      });

      /* ── Donut chart: distribusi tier ── */
      if (_areaDonutChart) _areaDonutChart.destroy();
      _areaDonutChart = new Chart(document.getElementById('areaDonutChart'), {
        type: 'doughnut',
        data: {
          labels,
          datasets: [{
            data: counts,
            backgroundColor: colors.map(c => c + 'cc'),
            borderColor: '#fff',
            borderWidth: 3,
            hoverOffset: 8,
          }]
        },
        options: {
          cutout: '60%',
          plugins: {
            legend: {
              display: true,
              position: 'right',
              labels: {
                font: { size: 11, family: "'Plus Jakarta Sans', sans-serif" },
                boxWidth: 12, padding: 10,
                generateLabels: chart => {
                  const ds = chart.data.datasets[0];
                  return chart.data.labels.map((lbl, i) => ({
                    text: `${lbl}: ${ds.data[i]}`,
                    fillStyle: ds.backgroundColor[i],
                    strokeStyle: ds.borderColor,
                    hidden: false, index: i,
                  }));
                }
              }
            },
            tooltip: { callbacks: { label: c => ` ${c.label}: ${c.parsed} karyawan` } },
            title: {
              display: true,
              text: 'Distribusi Tier',
              font: { size: 13, weight: '600', family: "'Plus Jakarta Sans', sans-serif" },
              color: '#1a1a2e', padding: { bottom: 12 }
            }
          }
        }
      });
    }

    /* ═══════════════════════════════════════════════════
       DONUT CHART
    ═══════════════════════════════════════════════════ */
    new Chart(document.getElementById('donutChart'), {
      type:'doughnut',
      data:{
        labels : {{ chart_labels | tojson }},
        datasets:[{ data:{{ chart_data | tojson }},
          backgroundColor:{{ chart_colors | tojson }},
          borderWidth:3, borderColor:'#fff', hoverOffset:8 }]
      },
      options:{ cutout:'60%',
        plugins:{ legend:{display:false},
          tooltip:{callbacks:{label:c=>` ${c.label}: ${c.parsed}`}} },
        animation:{animateRotate:true,duration:900} }
    });

    /* ═══════════════════════════════════════════════════
       HIDE BARIS > 5 (main section tables)
    ═══════════════════════════════════════════════════ */
    document.querySelectorAll('.perf-table tbody tr[data-i]').forEach(r=>{
      if(+r.dataset.i > 5) r.style.display='none';
    });

    function toggleRows(btn){
      const cls=btn.dataset.cls, tot=+btn.dataset.total;
      const exp=btn.dataset.expanded==='1';
      const rows=document.querySelectorAll(`#tbl-${cls} tbody tr[data-i]`);
      const ctr=document.getElementById(`ctr-${cls}`);
      if(!exp){
        rows.forEach(r=>r.style.display='');
        btn.textContent='Sembunyikan ▲'; btn.dataset.expanded='1';
        if(ctr) ctr.textContent=`Menampilkan ${tot} dari ${tot} karyawan`;
      } else {
        rows.forEach(r=>r.style.display=+r.dataset.i>5?'none':'');
        btn.textContent=`Lihat semua ${tot} karyawan ▼`; btn.dataset.expanded='0';
        if(ctr) ctr.textContent=`Menampilkan 5 dari ${tot} karyawan`;
      }
    }

    /* ═══════════════════════════════════════════════════
       RE-CLUSTER
    ═══════════════════════════════════════════════════ */
    function doRecluster(btn){
      if(!confirm('Re-run clustering dari Report_Clean.xlsx?\nProses ini akan memperbarui seluruh data.')) return;
      btn.disabled=true; btn.textContent='⏳ Memulai…';
      fetch('/recluster', {method:'POST', headers:{'X-Requested-With':'XMLHttpRequest'}})
      .then(()=>{ window.location.href='/'; })
      .catch(()=>{ window.location.href='/'; });
    }

    function handleImport(input){
      if(!input.files||!input.files.length) return;
      const name=input.files[0].name.toLowerCase();
      if(!name.endsWith('.csv')&&!name.endsWith('.xlsx')&&!name.endsWith('.xls')){
        alert('Pilih file berformat .csv, .xlsx, atau .xls');
        input.value=''; return;
      }
      document.getElementById('importForm').submit();
    }

    function btnFeedback(btn, text, delay){
      const orig=btn.textContent;
      btn.textContent=text; btn.style.opacity='0.7';
      setTimeout(()=>{ btn.textContent=orig; btn.style.opacity='1'; }, delay);
      return true;
    }

    document.querySelectorAll('.flash').forEach(el=>{
      setTimeout(()=>{ el.style.transition='opacity 0.4s'; el.style.opacity='0';
        setTimeout(()=>el.remove(),400); }, 5000);
    });
  </script>

  <style>
    /* ═══ JARAK ANTAR KARTU MAIN SECTION ═══════════════ */
    #section-main .table-card {
      margin-top: 20px;
    }
    #section-main .summary-card {
      margin-bottom: 4px;
    }

    /* ═══ AREA CHART ════════════════════════════════════ */
    .area-chart-title {
      font-size: 1rem;
      font-weight: 700;
      color: #1a1a2e;
      margin: 0 0 16px;
    }
    .area-chart-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }
    .area-chart-box {
      background: #fafafa;
      border: 1px solid #f0f0f0;
      border-radius: 14px;
      padding: 18px 20px;
    }
    @media (max-width: 700px) {
      .area-chart-row { grid-template-columns: 1fr; }
    }

    /* ═══ MAIN SECTION — jarak antar table card ════════ */
    #section-main .table-card {
      margin-top: 8px;
    }
    #section-main .card + .card {
      margin-top: 0; /* gap sudah dihandle flex gap di .main-content */
    }
    /* Tambah gap khusus antara summary card dan tabel pertama,
       serta antar tabel agar terasa lebih bernapas */
    #section-main {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    /* ═══ AREA FILTER SECTION ══════════════════════════ */
    .area-filter-card {
      position: relative;
      overflow: visible;
    }
    .area-filter-title {
      font-size: 1.25rem;
      font-weight: 700;
      color: #1a1a2e;
      margin: 0 0 4px;
    }
    .area-filter-sub {
      font-size: 0.85rem;
      color: #888;
      margin: 0 0 20px;
    }

    /* Search box */
    .area-search-wrap {
      position: relative;
      max-width: 420px;
    }
    .area-search-box {
      display: flex;
      align-items: center;
      border: 1.5px solid #e0e0e0;
      border-radius: 12px;
      padding: 10px 14px;
      gap: 8px;
      background: #fafafa;
      transition: border-color 0.2s;
    }
    .area-search-box:focus-within {
      border-color: #E91E8C;
      background: #fff;
    }
    .area-search-icon { font-size: 0.95rem; }
    .area-search-input {
      flex: 1;
      border: none;
      background: transparent;
      font-size: 0.9rem;
      font-family: inherit;
      outline: none;
      color: #1a1a2e;
    }
    .area-search-clear {
      background: none;
      border: none;
      cursor: pointer;
      color: #aaa;
      font-size: 0.85rem;
      padding: 0;
      line-height: 1;
    }
    .area-search-clear:hover { color: #E91E8C; }

    /* Dropdown */
    .area-dropdown {
      position: absolute;
      top: calc(100% + 6px);
      left: 0; right: 0;
      background: #fff;
      border: 1.5px solid #e0e0e0;
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.10);
      max-height: 260px;
      overflow-y: auto;
      z-index: 100;
      display: none;
    }
    .area-dropdown.open { display: block; }
    .area-dd-item {
      padding: 10px 16px;
      font-size: 0.875rem;
      cursor: pointer;
      color: #333;
      transition: background 0.15s;
    }
    .area-dd-item:hover { background: #fce4f3; color: #E91E8C; }
    .area-dd-item:first-child { border-radius: 10px 10px 0 0; }
    .area-dd-item:last-child  { border-radius: 0 0 10px 10px; }

    /* Chip */
    .area-chips {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 14px;
      flex-wrap: wrap;
    }
    .area-chip-label { font-size: 0.8rem; color: #888; }
    .area-chip-val {
      background: #fce4f3;
      color: #E91E8C;
      border: 1px solid #f9a8d4;
      border-radius: 20px;
      padding: 3px 12px;
      font-size: 0.82rem;
      font-weight: 600;
    }
    .area-chip-clear {
      background: none;
      border: 1px solid #e0e0e0;
      border-radius: 20px;
      padding: 3px 10px;
      font-size: 0.78rem;
      cursor: pointer;
      color: #888;
      transition: all 0.15s;
    }
    .area-chip-clear:hover { border-color: #E91E8C; color: #E91E8C; }

    /* Placeholder & empty */
    .area-placeholder {
      display: flex;
      justify-content: center;
      padding: 60px 0;
    }
    .area-placeholder-inner {
      text-align: center;
      color: #bbb;
    }
    .area-placeholder-icon { font-size: 2.5rem; display: block; margin-bottom: 10px; }
    .area-placeholder-inner p { font-size: 0.9rem; }
    .area-empty {
      text-align: center;
      padding: 40px;
      color: #aaa;
      font-size: 0.9rem;
    }

    /* Region tag */
    .region-tag {
      background: #ede9fe;
      color: #6d28d9;
      border-radius: 6px;
      padding: 2px 8px;
      font-size: 0.75rem;
      font-weight: 600;
      white-space: nowrap;
    }

    /* ═══ AREA CHART CARD ══════════════════════════════ */
    .area-chart-card {
      overflow: visible;
    }
    .area-chart-title {
      font-size: 1rem;
      font-weight: 700;
      color: #1a1a2e;
      margin-bottom: 16px;
    }
    .area-chart-title span {
      color: #E91E8C;
    }
    .area-chart-wrap {
      position: relative;
      width: 100%;
    }
    .area-chart-stats {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 20px;
    }
    .area-stat-pill {
      display: flex;
      align-items: center;
      gap: 7px;
      border: 1.5px solid #eee;
      border-radius: 12px;
      padding: 8px 14px;
      font-size: 12.5px;
      font-weight: 500;
      color: #444;
      flex-wrap: wrap;
    }
    .area-stat-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      flex-shrink: 0;
    }
    .area-stat-tier {
      font-weight: 700;
      color: #1a1a2e;
      margin-right: 2px;
    }
    .area-stat-sep {
      color: #ccc;
    }
    .area-stat-pill strong {
      color: #E91E8C;
    }

    /* Section area: juga pakai flex column gap */
    #section-area {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
  </style>

</body>
</html>