// Restaurant Recommender UI: the Stitch screens (stitch_bangalore_restaurant_recommender_ui/) rendered as a
// Streamlit v2 component. Markup and Tailwind classes follow the Stitch exports; Python supplies real data
// through `data` and receives searches through trigger values. Every dynamic string goes through h().

const FONT_LINKS = [
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Plus+Jakarta+Sans:wght@600;700&display=swap',
  'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap',
];
const QUICK = ['Family-friendly', 'Date night', 'Craft Beer & Rooftop', 'Quick bite', 'Outdoor garden seating'];
const RESULT_QUICK = ['Quick bite', 'Rooftop brew', 'Family-friendly'];
const FILL = `style="font-variation-settings: 'FILL' 1;"`;

const h = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const icon = (name, cls = '', fill = false) => `<span class="material-symbols-outlined ${cls}"${fill ? ' ' + FILL : ''}>${name}</span>`;
const clone = (o) => JSON.parse(JSON.stringify(o));
const fmtRating = (v) => (Number(v) === 0 ? 'Any Rating' : `${Number(v).toFixed(1)} ★ & above`);

function ensureFonts() {
  FONT_LINKS.forEach((href, i) => {
    const id = `rr-font-${i}`;
    if (document.getElementById(id)) return;
    const link = Object.assign(document.createElement('link'), { id, rel: 'stylesheet', href });
    document.head.appendChild(link);
  });
}

function appendText(current, chip, limit) {
  current = (current || '').trim();
  if (current.toLowerCase().includes(chip.toLowerCase())) return current;
  return (current ? `${current}, ${chip}` : chip).slice(0, limit);
}

function removeText(current, chip) {
  return (current || '').split(/\s*,\s*/).filter((p) => p && p.toLowerCase() !== chip.toLowerCase()).join(', ');
}

// ---------------------------------------------------------------------------------------------------------
// Shared pieces
// ---------------------------------------------------------------------------------------------------------
function logo() {
  return `<div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-primary-container to-primary flex items-center justify-center shadow-[0_0_12px_rgba(255,83,90,0.4)] shrink-0">${icon('restaurant', 'text-[20px] text-on-primary font-bold')}</div>`;
}

function aiPill(D, results) {
  if (D.ai.active) {
    return results
      ? `<div class="hidden sm:inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-tertiary-container/15 text-tertiary font-label-sm text-label-sm border border-tertiary/20"><span class="w-2 h-2 rounded-full bg-tertiary animate-pulse"></span>Zomato AI Active</div>`
      : `<div class="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-tertiary-container/20 text-tertiary font-label-sm text-label-sm"><span class="w-2 h-2 rounded-full bg-tertiary animate-pulse"></span>Zomato AI Active</div>`;
  }
  return `<div class="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-secondary-container/20 text-secondary font-label-sm text-label-sm border border-secondary/20" title="No GROQ_API_KEY configured"><span class="w-2 h-2 rounded-full bg-secondary"></span>AI Offline · Data Mode</div>`;
}

function header(D, results) {
  if (results) {
    return `<header class="fixed top-0 left-0 right-0 z-40 bg-surface-container-lowest/90 backdrop-blur-xl border-b border-surface-container-high/60 shadow-[0_2px_12px_rgba(0,0,0,0.6)]"><div class="max-w-[1200px] mx-auto px-gutter h-16 flex items-center justify-between gap-space-md"><div class="flex items-center gap-3">${logo()}<div class="flex items-center gap-space-sm"><span class="font-headline-sm text-headline-sm text-on-surface font-bold tracking-tight whitespace-nowrap">Restaurant Recommender</span><span class="hidden sm:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant font-caption text-caption border border-surface-container-highest">${icon('location_on', 'text-[13px] text-primary')}Bengaluru, KA</span></div></div><div class="flex items-center gap-space-md">${aiPill(D, true)}<button class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface hover:text-primary font-label-sm text-label-sm transition-colors border border-surface-container-highest" data-act="reset-all" type="button">${icon('restart_alt', 'text-[16px]')}Reset</button></div></div></header>`;
  }
  return `<header class="fixed top-0 left-0 right-0 z-50 bg-surface-container-lowest/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.65)]"><div class="max-w-[1200px] mx-auto px-gutter h-16 flex items-center justify-between gap-space-md"><div class="flex items-center gap-space-md">${logo()}<div class="flex items-center gap-space-sm"><span class="font-headline-sm text-headline-sm text-on-surface tracking-tight whitespace-nowrap">Restaurant Recommender</span><span class="hidden sm:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant font-caption text-caption">${icon('location_on', 'text-[13px] text-primary')}Bengaluru, KA</span></div></div><div class="flex items-center gap-space-md">${aiPill(D, false)}<button class="font-label-sm text-label-sm text-on-surface-variant hover:text-on-surface px-2.5 py-1 rounded-lg hover:bg-surface-container transition-colors" data-act="reset-form" type="button">Reset</button></div></div></header>`;
}

function footer(results) {
  const text = 'Data: Zomato restaurant dataset · Powered by AI · Built for food lovers in Bangalore';
  return results
    ? `<footer class="w-full bg-surface-container-lowest border-t border-surface-container-high/60 py-space-md"><div class="max-w-[1200px] mx-auto px-gutter flex flex-col sm:flex-row items-center justify-between gap-space-sm text-center sm:text-left"><p class="font-caption text-caption text-on-surface-variant">${text}</p></div></footer>`
    : `<footer class="w-full bg-surface-container-lowest py-space-2xl"><div class="mx-auto px-gutter flex flex-col sm:flex-row items-center justify-between gap-space-md text-center sm:text-left max-w-[1200px]"><p class="font-body-sm text-body-sm text-on-surface-variant">${text}</p></div></footer>`;
}

// Status banners (DESIGN.md "AI Context & Status Banners"), shaped like the Stitch AI summary banner.
const TONES = {
  success: { box: 'bg-tertiary-container/10 border-tertiary/20', bar: 'bg-tertiary', tile: 'bg-tertiary-container/30 border-tertiary/30 text-tertiary', title: 'text-tertiary', icon: 'auto_awesome' },
  warning: { box: 'bg-[#F59E0B]/10 border-[#F59E0B]/25', bar: 'bg-[#F59E0B]', tile: 'bg-[#F59E0B]/20 border-[#F59E0B]/30 text-[#F59E0B]', title: 'text-[#F59E0B]', icon: 'info' },
  info: { box: 'bg-[#3B82F6]/10 border-[#3B82F6]/25', bar: 'bg-[#3B82F6]', tile: 'bg-[#3B82F6]/20 border-[#3B82F6]/30 text-[#60A5FA]', title: 'text-[#60A5FA]', icon: 'tune' },
  error: { box: 'bg-[#EF4444]/10 border-[#EF4444]/25', bar: 'bg-[#EF4444]', tile: 'bg-[#EF4444]/20 border-[#EF4444]/30 text-[#F87171]', title: 'text-[#F87171]', icon: 'error' },
};

function banner(tone, title, bodyHtml, extraHtml = '', pill = '') {
  const t = TONES[tone];
  return `<div class="relative overflow-hidden rounded-xl ${t.box} border p-space-md mb-space-md shadow-md" data-banner="${tone}"><div class="absolute left-0 top-0 bottom-0 w-1.5 ${t.bar}"></div><div class="flex items-start gap-space-md pl-1.5"><div class="w-9 h-9 rounded-lg ${t.tile} border flex items-center justify-center shrink-0">${icon(t.icon, 'text-[20px]', true)}</div><div class="flex flex-col gap-1"><div class="flex items-center gap-2"><span class="font-headline-sm text-headline-sm ${t.title} font-semibold">${h(title)}</span>${pill}</div>${bodyHtml ? `<p class="font-body-md text-body-md text-on-surface">${bodyHtml}</p>` : ''}${extraHtml}</div></div></div>`;
}

// ---------------------------------------------------------------------------------------------------------
// Home: "Intuitive Preference Studio"
// ---------------------------------------------------------------------------------------------------------
function locationField(S) {
  const D = S.data, p = S.draft;
  const items = D.locations.map((loc) => {
    const sel = loc === p.location;
    return `<button class="w-full flex items-center justify-between px-3 py-2 rounded-lg text-left font-body-sm text-body-sm text-on-surface ${sel ? 'bg-surface-container hover:bg-surface-bright' : 'hover:bg-surface-container'} transition-colors" data-act="pick-location" data-value="${h(loc)}" data-search="${h(loc.toLowerCase())}" type="button"><span class="">${h(loc)}</span>${sel ? icon('check', 'text-[16px] text-primary') : ''}</button>`;
  }).join('');
  return `<div class="space-y-space-xs relative"><div class="flex items-center justify-between"><label class="font-label-md text-label-md text-on-surface flex items-center gap-1.5" for="locationTrigger">${icon('pin_drop', 'text-[16px] text-primary')}Location in Bangalore</label><span class="font-caption text-caption text-on-surface-variant">${h(D.stats.hubs)} food hubs</span></div><div class="relative" data-dd="location"><button class="w-full h-12 bg-surface-container rounded-lg px-space-md flex items-center justify-between text-left text-on-surface hover:bg-surface-container-high transition-colors focus:outline-none shadow-sm group" id="locationTrigger" data-act="toggle-location" type="button"><span class="font-body-md text-body-md text-on-surface flex items-center gap-2">${icon('near_me', 'text-[18px] text-primary-container')}${h(p.location)}</span>${icon(S.dd === 'location' ? 'expand_less' : 'expand_more', 'text-on-surface-variant group-hover:text-on-surface transition-transform')}</button><div class="${S.dd === 'location' ? '' : 'hidden '}absolute top-full left-0 right-0 mt-1.5 z-30 bg-surface-container-high rounded-xl p-1.5 shadow-[0_16px_36px_-8px_rgba(0,0,0,0.8)] backdrop-blur-md"><div class="p-1.5 mb-1"><div class="flex items-center gap-2 bg-surface-container-lowest px-3 py-1.5 rounded-lg">${icon('search', 'text-[16px] text-on-surface-variant')}<input class="bg-transparent border-0 outline-none text-on-surface font-body-sm text-body-sm w-full placeholder:text-outline" data-filter="location" placeholder="Type neighborhood..." type="text"></div></div><div class="max-h-48 overflow-y-auto space-y-0.5" data-list="location">${items}</div></div></div><p class="font-caption text-caption text-on-surface-variant flex items-center gap-1 pt-1">${icon('bolt', 'text-[12px] text-tertiary')}Locality lookup covers micro-pubs, bistros, and iconic messes.</p></div>`;
}

function budgetField(S) {
  const p = S.draft;
  const sel = S.data.budgets.find((b) => b.value === p.budget);
  const opts = S.data.budgets.map((b) => {
    const on = b.value === p.budget;
    return on
      ? `<button class="budget-option py-1 px-2 rounded-lg text-center flex flex-col items-center justify-center transition-all bg-primary-container text-on-primary-container shadow-[0_0_14px_rgba(255,83,90,0.35)] focus:outline-none" data-act="pick-budget" data-value="${b.value}" type="button"><div class="flex items-center gap-1"><span class="font-label-sm text-label-sm font-semibold">${h(b.label)}</span>${icon('check', 'text-[13px]')}</div><span class="font-caption text-caption opacity-90 whitespace-nowrap max-sm:text-[10px] max-sm:tracking-normal">${h(b.range)}</span></button>`
      : `<button class="budget-option py-1 px-2 rounded-lg text-center flex flex-col items-center justify-center transition-all text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high focus:outline-none" data-act="pick-budget" data-value="${b.value}" type="button"><span class="font-label-sm text-label-sm font-semibold">${h(b.label)}</span><span class="font-caption text-caption opacity-80 whitespace-nowrap max-sm:text-[10px] max-sm:tracking-normal">${h(b.range)}</span></button>`;
  }).join('');
  return `<div class="space-y-space-xs"><div class="flex items-center justify-between"><label class="font-label-md text-label-md text-on-surface flex items-center gap-1.5">${icon('payments', 'text-[16px] text-secondary')}Budget for Two</label><span class="font-caption text-caption px-2 py-0.5 rounded-full bg-secondary-container/20 text-secondary">${h(sel ? sel.range : '')}</span></div><div class="grid grid-cols-3 gap-2 bg-surface-container p-1.5 rounded-xl h-12">${opts}</div></div>`;
}

// Cuisine pills: "Any Cuisine" + the most common cuisines in the data; "+ More" opens a searchable list of all.
function cuisinePills(S, modal) {
  const D = S.data, cur = S.draft.cuisine;
  const names = [...D.cuisines.top];
  if (cur && !names.includes(cur)) names.push(cur);
  const on = modal
    ? 'cuisine-pill px-3.5 py-1.5 rounded-full font-label-sm text-label-sm transition-all bg-[#E23744] text-white shadow-[0_0_10px_rgba(226,55,68,0.35)]'
    : 'cuisine-pill px-3.5 py-2 rounded-full font-label-sm text-label-sm transition-all bg-primary-container text-on-primary-container shadow-[0_0_10px_rgba(255,83,90,0.3)]';
  const off = modal
    ? 'cuisine-pill px-3.5 py-1.5 rounded-full font-label-sm text-label-sm transition-all bg-[#17171C] text-on-surface-variant hover:text-on-surface border border-[#2A2A32] hover:bg-[#2A2A32]'
    : 'cuisine-pill px-3.5 py-2 rounded-full font-label-sm text-label-sm transition-all bg-surface-container text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface';
  const pills = [`<button class="${cur ? off : on}" data-act="pick-cuisine" data-value="" type="button">Any Cuisine</button>`]
    .concat(names.map((c) => `<button class="${c === cur ? on : off}" data-act="pick-cuisine" data-value="${h(c)}" type="button">${h(c)}</button>`))
    .concat([`<button class="${off}" data-act="toggle-cuisines" type="button">${S.dd === 'cuisine' ? '− Fewer' : `+ ${D.cuisines.all.length - D.cuisines.top.length} more`}</button>`])
    .join('');
  const list = D.cuisines.all.map((c) => `<button class="w-full flex items-center justify-between px-3 py-2 rounded-lg text-left font-body-sm text-body-sm text-on-surface ${c === cur ? 'bg-surface-container hover:bg-surface-bright' : 'hover:bg-surface-container'} transition-colors" data-act="pick-cuisine" data-value="${h(c)}" data-search="${h(c.toLowerCase())}" type="button"><span class="">${h(c)}</span>${c === cur ? icon('check', 'text-[16px] text-primary') : ''}</button>`).join('');
  const dd = `<div class="${S.dd === 'cuisine' ? '' : 'hidden '}absolute top-full left-0 right-0 mt-1.5 z-30 bg-surface-container-high rounded-xl p-1.5 shadow-[0_16px_36px_-8px_rgba(0,0,0,0.8)] backdrop-blur-md"><div class="p-1.5 mb-1"><div class="flex items-center gap-2 bg-surface-container-lowest px-3 py-1.5 rounded-lg">${icon('search', 'text-[16px] text-on-surface-variant')}<input class="bg-transparent border-0 outline-none text-on-surface font-body-sm text-body-sm w-full placeholder:text-outline" data-filter="cuisine" placeholder="Search ${D.cuisines.all.length} cuisines..." type="text"></div></div><div class="max-h-48 overflow-y-auto space-y-0.5" data-list="cuisine">${list}</div></div>`;
  return `<div class="relative" data-dd="cuisine"><div class="flex flex-wrap gap-2">${pills}</div>${dd}</div>`;
}

function sliderCard(kind, S, modal) {
  const p = S.draft;
  const box = modal ? 'space-y-2 bg-[#1F1F26] p-4 rounded-xl border border-[#2A2A32]' : 'space-y-space-xs bg-surface-container/60 p-space-md rounded-xl';
  const input = modal ? 'w-full h-1.5 bg-[#2A2A32] rounded-lg appearance-none cursor-pointer accent-[#E23744]' : 'w-full h-1.5 bg-surface-container-highest rounded-lg appearance-none cursor-pointer accent-primary-container';
  const tick = (t) => (modal ? `<span class="text-[11px]">${t}</span>` : `<span class="">${t}</span>`);
  if (kind === 'rating') {
    const badge = modal
      ? 'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-[#17171C] text-secondary font-label-sm text-label-sm border border-secondary/30 shadow-[0_0_8px_rgba(255,185,87,0.2)]'
      : 'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-surface-container-high text-secondary font-label-sm text-label-sm shadow-[0_0_8px_rgba(245,165,36,0.25)]';
    return `<div class="${box}"><div class="flex items-center justify-between"><label class="font-label-md text-label-md text-on-surface flex items-center gap-1.5">${icon('star', 'text-[18px] text-secondary', true)}Minimum Rating</label><span class="${badge}" data-out="rating">${fmtRating(p.min_rating)}</span></div><div class="${modal ? 'py-1' : 'py-2'}"><input class="${input}" data-input="min_rating" max="5" min="0" step="0.5" type="range" value="${h(p.min_rating)}"></div><div class="flex justify-between font-caption text-caption text-on-surface-variant px-0.5">${tick('Any (0.0)')}${tick('Popular (3.5)')}${tick('Elite (4.5+)')}</div></div>`;
  }
  const badge = modal
    ? 'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-[#17171C] text-on-surface font-label-sm text-label-sm border border-[#2A2A32]'
    : 'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-surface-container-high text-on-surface font-label-sm text-label-sm';
  return `<div class="${box}"><div class="flex items-center justify-between"><label class="font-label-md text-label-md text-on-surface flex items-center gap-1.5">${icon(modal ? 'filter_list' : 'tune', 'text-[18px] text-tertiary')}Batch Size</label><span class="${badge}" data-out="top_n">${h(p.top_n)} recommendations</span></div><div class="${modal ? 'py-1' : 'py-2'}"><input class="${input}" data-input="top_n" max="10" min="3" step="1" type="range" value="${h(p.top_n)}"></div><div class="flex justify-between font-caption text-caption text-on-surface-variant px-0.5">${tick('3 picks')}${tick('Balanced (5)')}${tick('10 deep dive')}</div></div>`;
}

function trendingCard(t) {
  return `<div class="bg-surface-container-low rounded-xl overflow-hidden shadow-lg flex flex-col group hover:bg-surface-container transition-all"><div class="h-32 w-full relative bg-surface-container-highest"><img class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" alt="Representative photo" src="${h(t.image)}"><div class="absolute inset-0 bg-gradient-to-t from-surface-container-low via-transparent to-transparent"></div><div class="absolute top-2.5 right-2.5 px-2 py-0.5 rounded-md bg-surface-container-lowest/90 backdrop-blur-sm text-secondary font-label-sm text-label-sm flex items-center gap-1">${icon('star', 'text-[13px]', true)} ${h(t.rating)}</div><div class="absolute bottom-2 left-2.5 px-2 py-0.5 rounded ${t.tag_tone === 'secondary' ? 'bg-secondary-container/90 text-on-secondary-container' : 'bg-primary-container/80 text-on-primary-container'} font-caption text-caption font-semibold">${h(t.tag)}</div></div><div class="p-space-md flex-1 flex flex-col justify-between"><div><div class="flex items-center justify-between mb-1 gap-2"><h3 class="font-headline-sm text-headline-sm text-on-surface truncate">${h(t.name)}</h3><span class="font-caption text-caption text-on-surface-variant shrink-0">${h(t.cost)}</span></div><p class="font-body-sm text-body-sm text-on-surface-variant line-clamp-2">${h(t.blurb)}</p></div><div class="mt-space-md pt-space-xs flex items-center justify-between text-on-surface-variant font-caption text-caption"><span class="flex items-center gap-1">${icon('check_circle', 'text-[13px] text-tertiary')} ${h(t.votes)}</span><span class="">${h(t.location)}</span></div></div></div>`;
}

function homeView(S) {
  const D = S.data, p = S.draft, loading = S.loading === 'home';
  const trending = D.trending[p.location] || [];
  const submit = loading
    ? `${icon('progress_activity', 'animate-spin text-[20px]')}<span>Consulting Bangalore foodie network...</span>`
    : `${icon('search', 'text-[20px] transition-transform group-hover:scale-110')}<span class="">Find restaurants</span><span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-on-primary-container/20 text-on-primary-container font-caption text-caption uppercase tracking-wider">${icon('auto_awesome', 'text-[13px]')}AI Engine</span>`;
  const chips = QUICK.map((c) => `<button class="px-2.5 py-1 rounded-lg bg-surface-container text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high font-caption text-caption transition-colors" data-act="add-extra" data-value="${h(c)}" type="button">+ ${h(c)}</button>`).join('');
  return `${header(D, false)}<main class="w-full pt-16 bg-surface-container-lowest min-h-screen"><div class="mx-auto px-gutter py-space-xl max-w-[1200px]"><div class="flex flex-col w-full relative">
<div class="pointer-events-none absolute -top-12 left-1/2 -translate-x-1/2 w-[520px] h-[280px] bg-primary-container/15 rounded-full blur-[110px] -z-10"></div>
<div class="pointer-events-none absolute top-40 right-4 w-[280px] h-[220px] bg-secondary-container/10 rounded-full blur-[90px] -z-10"></div>
<div class="flex flex-col items-center text-center space-y-space-md mb-space-xl"><div class="inline-flex items-center gap-space-xs px-3.5 py-1.5 rounded-full bg-surface-container-high shadow-md"><div class="w-6 h-6 rounded-full bg-primary-container/20 flex items-center justify-center text-primary shadow-[0_0_12px_rgba(255,83,90,0.45)]">${icon('restaurant_menu', 'text-[15px]', true)}</div><span class="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Curated Discovery Engine</span><span class="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse"></span></div><div class="space-y-space-xs max-w-xl"><h1 class="font-headline-xl text-headline-xl-mobile sm:text-headline-xl text-on-surface tracking-tight sm:tracking-tight">Restaurant Recommender</h1><p class="font-body-lg text-body-lg text-on-surface-variant">Personalised restaurant picks for Bangalore, ranked and explained by AI from real Zomato data.</p></div><div class="flex flex-wrap items-center justify-center gap-space-md pt-space-xs"><div class="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-surface-container-low text-on-surface-variant font-caption text-caption">${icon('dataset', 'text-[14px] text-tertiary')}<span class="">${h(D.stats.outlets)} Verified Outlets</span></div><div class="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-surface-container-low text-on-surface-variant font-caption text-caption">${icon('verified', 'text-[14px] text-secondary')}<span class="">Real Zomato Ratings</span></div><div class="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-surface-container-low text-on-surface-variant font-caption text-caption">${icon('near_me', 'text-[14px] text-primary')}<span class="">${h(D.stats.hubs)} Micro-markets</span></div></div></div>
${S.error ? banner('error', 'Something went wrong', 'We could not find restaurants just now. Please try again in a moment.') : ''}
<div class="w-full bg-surface-container-low rounded-xl p-space-lg sm:p-space-xl shadow-2xl relative overflow-hidden"><div class="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-transparent via-primary-container to-transparent opacity-80"></div>
<form class="space-y-space-xl" data-form="home"><div class="space-y-space-xl">
<div class="space-y-space-sm"><div class="flex items-center gap-2 pb-1"><h3 class="font-headline-sm text-headline-sm text-on-surface">Location &amp; Budget</h3></div><div class="grid grid-cols-1 md:grid-cols-2 gap-space-md bg-surface-container/60 p-space-md rounded-xl">${locationField(S)}${budgetField(S)}</div></div>
<div class="space-y-space-sm"><div class="flex items-center justify-between"><div class="flex items-center gap-2"><h3 class="font-headline-sm text-headline-sm text-on-surface flex items-center gap-1.5">${icon('ramen_dining', 'text-[18px] text-tertiary')}Cuisine &amp; Taste</h3></div><span class="font-caption text-caption text-on-surface-variant">${h(D.cuisines.all.length)} cuisines</span></div><div class="bg-surface-container/60 p-space-md rounded-xl">${cuisinePills(S, false)}</div></div>
<div class="space-y-space-sm"><div class="flex items-center gap-2"><h3 class="font-headline-sm text-headline-sm text-on-surface">Precision &amp; Criteria</h3></div><div class="grid grid-cols-1 md:grid-cols-2 gap-space-md">${sliderCard('rating', S, false)}${sliderCard('top_n', S, false)}</div></div>
<div class="space-y-space-sm"><div class="flex items-center justify-between gap-space-sm"><div class="flex items-center gap-2"><label class="font-headline-sm text-headline-sm text-on-surface flex items-center gap-1.5" for="promptInput">${icon('psychology', 'text-[18px] text-primary')}Ambience &amp; Extra Preferences <span class="font-caption text-caption text-on-surface-variant font-normal">(optional)</span></label></div><span class="font-caption text-caption text-outline" data-out="count">${p.extra.length}/${D.max_extra}</span></div><div class="bg-surface-container/60 p-space-md rounded-xl space-y-space-sm"><div class="relative"><input class="w-full bg-surface-container rounded-xl px-space-md py-3 text-on-surface font-body-md text-body-md placeholder:text-outline focus:outline-none focus:bg-surface-container-high transition-all shadow-sm" id="promptInput" data-input="extra" maxlength="${D.max_extra}" placeholder="e.g. family-friendly, quick service, craft beer, good for a date" type="text" value="${h(p.extra)}"></div><div class="flex flex-wrap gap-1.5 pt-1">${chips}</div></div></div>
<div class="pt-space-sm space-y-space-md"><button class="w-full h-14 rounded-xl bg-primary-container text-on-primary-container font-headline-sm text-headline-sm flex items-center justify-center gap-space-sm hover:brightness-110 active:scale-[0.99] transition-all shadow-[0_4px_24px_rgba(255,83,90,0.4)] relative group overflow-hidden" data-act="submit-home" type="submit"${loading ? ' disabled' : ''}>${submit}</button><div class="p-space-md rounded-xl bg-surface-container flex items-center justify-between gap-space-md"><div class="flex items-center gap-2.5"><div class="w-2.5 h-2.5 rounded-full bg-tertiary shadow-[0_0_8px_#4edea3]"></div><span class="font-body-sm text-body-sm text-on-surface">Zomato dataset indexed: ${h(D.stats.listings)} Bangalore listings processed</span></div><div class="hidden sm:flex items-center gap-1.5 text-on-surface-variant font-caption text-caption">${icon('bolt', 'text-[14px]')}<span class="">${h(D.ai.engine)}</span></div></div></div>
</div></form></div>
${trending.length ? `<div class="mt-space-xl space-y-space-md"><div class="flex items-center justify-between"><div class="flex items-center gap-2">${icon('local_fire_department', 'text-secondary text-[20px]')}<h2 class="font-headline-sm text-headline-sm text-on-surface">Top Rated Around ${h(p.location === D.locations[0] ? 'Bangalore' : p.location)}</h2></div><span class="font-caption text-caption text-on-surface-variant">From Zomato ratings</span></div><div class="grid grid-cols-1 md:grid-cols-3 gap-space-md">${trending.map(trendingCard).join('')}</div></div>` : ''}
</div></div></main>${footer(false)}`;
}

// ---------------------------------------------------------------------------------------------------------
// Results: "Floating Preferences Panel"
// ---------------------------------------------------------------------------------------------------------
const WHY_TONES = ['text-secondary', 'text-tertiary', 'text-secondary', 'text-primary-fixed', 'text-secondary'];
const BADGE_TONES = {
  top: 'bg-primary-container/20 text-primary border border-primary-container/40 shadow-[0_0_8px_rgba(255,83,90,0.2)]',
  tertiary: 'bg-surface-container text-tertiary border border-tertiary/30',
  secondary: 'bg-surface-container text-secondary border border-secondary/30',
  neutral: 'bg-surface-container text-on-surface-variant border border-surface-container-highest',
};

function card(it, S) {
  const top = it.rank === 1;
  const whyTone = WHY_TONES[(it.rank - 1) % WHY_TONES.length];
  const meta = [`<span class="text-on-surface font-medium">${h(it.location)}</span>`]
    .concat(it.types.map((t) => `<span class="">${h(t)}</span>`))
    .concat(it.feature ? [`<span class="text-tertiary flex items-center gap-1">${icon(it.feature.icon, 'text-[14px]')}${h(it.feature.text)}</span>`] : [])
    .concat([`<span class="text-tertiary font-semibold">${h(it.cost)}</span>`])
    .join('<span class="text-outline-variant">·</span>');
  const badge = top
    ? `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full ${BADGE_TONES.top} font-label-sm text-label-sm">${icon('star', 'text-[13px]', true)}#1 TOP PICK</span>`
    : it.badge ? `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full ${BADGE_TONES[it.badge.tone]} font-label-sm text-label-sm">${h(it.badge.text)}</span>` : '';
  const rankBox = top
    ? `<div class="flex flex-col items-center justify-center w-11 h-11 rounded-xl bg-primary-container/25 text-primary border border-primary-container/50 shrink-0 shadow-[0_0_12px_rgba(255,83,90,0.35)]"><span class="font-headline-md text-headline-md font-bold leading-none">#${it.rank}</span><span class="font-caption text-[9px] tracking-tight text-primary-fixed uppercase font-semibold">Rank</span></div>`
    : `<div class="flex flex-col items-center justify-center w-11 h-11 rounded-xl bg-surface-container-high text-on-surface border border-surface-container-highest shrink-0"><span class="font-headline-md text-headline-md font-bold leading-none">#${it.rank}</span><span class="font-caption text-[9px] tracking-tight text-on-surface-variant uppercase font-semibold">Rank</span></div>`;
  const view = top
    ? `<a class="px-space-md py-2 rounded-lg bg-primary text-on-primary hover:bg-primary-fixed font-label-sm text-label-sm font-semibold transition-all duration-200 flex items-center gap-1.5 shadow-[0_0_12px_rgba(226,55,68,0.35)]" href="${h(it.link)}" target="_blank" rel="noopener noreferrer"><span class="">View Zomato Menu</span>${icon('arrow_outward', 'text-[16px]')}</a>`
    : `<a class="px-space-md py-2 rounded-lg bg-surface-container-high hover:bg-surface-bright text-on-surface font-label-sm text-label-sm font-semibold transition-colors flex items-center gap-1.5 border border-surface-container-highest" href="${h(it.link)}" target="_blank" rel="noopener noreferrer"><span class="">View Details</span>${icon('arrow_outward', 'text-[16px]')}</a>`;
  const rating = it.rating == null
    ? `<span class="font-label-md text-label-md text-on-surface">Not rated yet</span>`
    : `<div class="flex items-baseline gap-1.5"><span class="font-headline-sm text-headline-sm font-bold text-on-surface">${h(it.rating)}</span>${icon('star', 'text-[13px] text-secondary', true)}${it.votes ? `<span class="font-caption text-caption text-on-surface-variant">(${h(it.votes)} Zomato votes)</span>` : ''}</div>`;
  return `<article class="relative group rounded-xl bg-surface-container-low ${top ? 'border border-primary-container/40 p-space-lg transition-all duration-300 hover:bg-surface-container shadow-[0_4px_24px_rgba(255,83,90,0.15)]' : 'border border-surface-container-high/60 p-space-lg transition-all duration-300 hover:bg-surface-container hover:shadow-xl shadow-md'}" data-card="${it.rank}">${top ? '<div class="absolute inset-x-0 -top-px h-1 rounded-t-xl bg-gradient-to-r from-transparent via-primary-container to-transparent opacity-90"></div>' : ''}<div class="flex flex-col md:flex-row gap-space-md items-start"><div class="w-full md:w-56 h-40 md:h-48 rounded-lg overflow-hidden shrink-0 relative bg-surface-container-high"><img class="w-full h-full object-cover" alt="Representative photo" src="${h(it.image)}"><div class="absolute inset-0 bg-gradient-to-t from-surface-container-lowest/80 via-transparent to-transparent"></div><span class="absolute bottom-2 left-2.5 font-caption text-caption text-on-surface flex items-center gap-1 bg-surface-container-lowest/70 backdrop-blur-sm px-2 py-0.5 rounded-full">${icon('photo_camera', 'text-[12px] text-tertiary')}Representative photo</span></div><div class="flex flex-col gap-2.5 flex-1 w-full min-w-0"><div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2"><div class="flex items-center gap-space-md">${rankBox}<div><div class="flex items-center gap-2 flex-wrap"><h2 class="font-headline-md text-headline-md text-on-surface font-bold tracking-tight">${h(it.name)}</h2>${badge}</div><div class="flex items-center gap-1.5 flex-wrap font-label-sm text-label-sm text-on-surface-variant mt-1">${meta}</div></div></div><div class="flex items-center gap-2 self-start sm:self-auto shrink-0">${view}</div></div><div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 p-2.5 rounded-lg bg-surface-container/70 border border-surface-container-highest"><div class="flex flex-col gap-0.5 min-w-0"><span class="font-caption text-caption text-on-surface-variant flex items-center gap-1">${icon('restaurant', 'text-[13px]')}Cuisine</span><span class="font-label-md text-label-md text-on-surface truncate" title="${h(it.cuisines)}">${h(it.cuisines)}</span></div><div class="flex flex-col gap-0.5"><span class="font-caption text-caption text-on-surface-variant flex items-center gap-1">${icon('star', 'text-[13px] text-secondary')}Rating &amp; Buzz</span>${rating}</div><div class="flex flex-col gap-0.5"><span class="font-caption text-caption text-on-surface-variant flex items-center gap-1">${icon('wallet', 'text-[13px]')}Estimated Cost</span><span class="font-label-md text-label-md text-tertiary font-semibold">${h(it.cost)}</span></div></div><div class="flex items-start gap-space-sm bg-surface-container-high/40 border border-surface-container-high p-2.5 rounded-lg">${icon('auto_awesome', `text-[18px] ${whyTone} shrink-0 mt-0.5`, true)}<div class="flex flex-col gap-0.5"><span class="font-label-sm text-label-sm ${whyTone} font-semibold">${h(it.why_label)}</span><p class="font-body-sm text-body-sm text-on-surface">${h(it.explanation)}</p></div></div><div class="flex items-center justify-between gap-space-md text-caption font-caption text-on-surface-variant pt-0.5"><span class="flex items-center gap-1 text-tertiary font-medium">${icon(it.footer_left.icon, 'text-[14px]')}${h(it.footer_left.text)}</span><span class="text-right">${h(it.footer_right)}</span></div></div></div></article>`;
}

function chipRow(S) {
  const D = S.data, c = S.chips;
  const budget = D.budgets.find((b) => b.value === c.budget);
  const quick = RESULT_QUICK.filter((q) => !c.extra.toLowerCase().includes(q.toLowerCase()));
  const chip = 'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface font-label-sm text-label-sm transition-colors border border-surface-container-highest';
  return `<div class="flex items-center justify-between gap-3 flex-wrap bg-surface-container-low p-2.5 rounded-xl border border-surface-container-high/60"><div class="flex items-center gap-2 flex-wrap">
<button class="${chip}" data-act="open-modal" type="button">${icon('location_on', 'text-[15px] text-primary')}<span>${h(c.location)}</span><span class="text-[10px] text-on-surface-variant">▾</span></button>
<button class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary-container/25 text-primary border border-primary-container/60 font-label-sm text-label-sm shadow-[0_0_10px_rgba(255,83,90,0.25)]" data-act="open-modal" type="button">${icon('payments', 'text-[15px] text-primary')}<span class="font-semibold">${h(budget ? budget.chip : '')}</span><span class="text-[10px] text-primary">▾</span></button>
<button class="${chip}" data-act="open-modal" type="button">${icon('restaurant_menu', 'text-[15px] text-on-surface-variant')}<span>Cuisine: ${h(c.cuisine || 'Any Cuisine')}</span><span class="text-[10px] text-on-surface-variant">▾</span></button>
<button class="${chip}" data-act="open-modal" type="button">${icon('star', 'text-[15px] text-secondary', true)}<span>${Number(c.min_rating) === 0 ? 'Any Rating' : `${Number(c.min_rating).toFixed(1)}+ Rating`}</span><span class="text-[10px] text-on-surface-variant">▾</span></button>
${c.extra ? `<div class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-tertiary-container/20 text-tertiary border border-tertiary/30 font-label-sm text-label-sm">${icon('check', 'text-[15px]')}<span>${h(c.extra)}</span><button class="ml-0.5 hover:text-on-surface text-tertiary/70 font-bold" data-act="chip-clear-extra" type="button" aria-label="Remove">✕</button></div>` : ''}
${quick.length ? '<div class="h-4 w-px bg-surface-container-highest mx-0.5 hidden lg:block"></div>' : ''}
${quick.map((q) => `<button class="inline-flex items-center px-2.5 py-1 rounded-lg bg-surface-container/60 hover:bg-surface-container text-on-surface-variant hover:text-on-surface text-caption font-caption transition-colors border border-dashed border-outline-variant/60" data-act="chip-add-extra" data-value="${h(q)}" type="button">+ ${h(q)}</button>`).join('')}
</div><div class="flex items-center gap-2 shrink-0"><button class="px-3 py-1.5 rounded-lg bg-primary text-on-primary hover:bg-primary-fixed font-label-sm text-label-sm font-semibold transition-colors shadow-sm flex items-center gap-1" data-act="chip-apply" type="button"${S.loading ? ' disabled' : ''}>${S.loading === 'chips' ? icon('progress_activity', 'animate-spin text-[14px]') : ''}Apply Filters</button></div></div>`;
}

function statusBanners(S) {
  const V = S.data.view, D = S.data;
  let out = '';
  if (S.error) out += banner('error', 'Something went wrong', 'We could not refresh your recommendations. Please try again in a moment.');
  V.notes.forEach((n) => { out += banner('info', 'Note', h(n)); });
  if (!V.items.length) {
    const sugg = V.suggestions.length
      ? `<div class="flex flex-wrap items-center gap-2 pt-1"><span class="font-body-sm text-body-sm text-on-surface-variant">Did you mean:</span>${V.suggestions.map((s) => `<button class="px-2.5 py-1 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface font-label-sm text-label-sm border border-surface-container-highest" data-act="use-location" data-value="${h(s)}" type="button">${h(s)}</button>`).join('')}</div>`
      : '';
    out += banner('warning', 'No matches', h(V.message || 'No restaurants matched your preferences.') + ' Try a lower minimum rating, a different budget, or Any Cuisine.', sugg);
    return out;
  }
  if (V.relaxed.length) {
    out += banner('info', 'Some preferences were relaxed to find matches', '', `<ul class="list-disc pl-5 font-body-sm text-body-sm text-on-surface">${V.relaxed.map((r) => `<li>${h(r)}</li>`).join('')}</ul>`);
  }
  if (!V.ai_explanations) {
    out += banner('warning', 'Data-based picks', `${h(V.fallback_reason)}, so these descriptions are generated from the data instead of by AI.`);
  } else if (V.summary) {
    out += banner('success', 'AI Dining Insight', h(V.summary), '', `<span class="text-tertiary/60">·</span><span class="font-caption text-caption px-2 py-0.5 rounded-full bg-tertiary/15 text-tertiary font-semibold">${h(D.ai.model)}</span>`);
  }
  return out;
}

function resultsView(S) {
  const D = S.data, V = D.view, busy = !!S.loading;
  const n = V.items.length;
  return `${header(D, true)}<main class="w-full pt-16 flex-1 bg-surface-container-lowest"><div class="max-w-[1200px] mx-auto px-gutter py-space-md"><div class="flex flex-col w-full">
<div class="flex flex-col gap-space-sm mb-space-md"><div class="flex flex-col sm:flex-row sm:items-end justify-between gap-space-sm pb-space-xs"><div><div class="flex items-center gap-2 mb-1"><span class="font-caption text-caption uppercase tracking-wider text-primary font-semibold">BANGALORE DINING INTELLIGENCE</span><span class="text-outline-variant">·</span><span class="font-caption text-caption text-on-surface-variant">Live Ranking</span></div><div class="flex items-center gap-space-md flex-wrap"><h1 class="font-headline-xl text-headline-xl-mobile sm:text-headline-xl text-on-surface font-bold tracking-tight sm:tracking-tight">Your recommendations</h1>${n ? `<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-surface-container-high text-primary font-label-sm text-label-sm shadow-sm border border-primary/20"><span class="w-1.5 h-1.5 rounded-full bg-primary animate-ping"></span>${n} curated spot${n === 1 ? '' : 's'}</span>` : ''}</div></div><button class="inline-flex items-center gap-1.5 self-start sm:self-auto px-space-md py-2 rounded-lg bg-surface-container text-on-surface hover:bg-surface-container-high hover:text-primary transition-all duration-200 font-label-md text-label-md border border-surface-container-highest shadow-sm active:scale-95" data-act="open-modal" type="button">${icon('tune', 'text-[17px] text-primary')}Edit Preferences</button></div>${chipRow(S)}</div>
${statusBanners(S)}
<div class="flex flex-col gap-space-md transition-opacity ${busy ? 'opacity-40' : ''}" data-cards>${V.items.map((it) => card(it, S)).join('')}</div>
${n ? `<div class="mt-space-md p-space-md rounded-xl bg-surface-container-low border border-surface-container-high/60 flex flex-col sm:flex-row items-center justify-between gap-space-md shadow-md"><div class="flex items-center gap-space-sm"><div class="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center shrink-0 border border-primary/30">${icon('psychology', 'text-[18px]')}</div><div><span class="font-headline-sm text-headline-sm text-on-surface font-semibold">Need more precision?</span><p class="font-caption text-caption text-on-surface-variant">Adjust budget, cuisine and rating, or add ambience notes like craft beer or rooftop seating.</p></div></div><div class="flex items-center gap-2 w-full sm:w-auto"><button class="w-full sm:w-auto px-space-md py-2 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface font-label-md text-label-md transition-colors flex items-center justify-center gap-1.5 border border-surface-container-highest" data-act="shuffle" type="button"${busy ? ' disabled' : ''}>${icon(S.loading === 'shuffle' ? 'progress_activity' : 'refresh', `text-[16px]${S.loading === 'shuffle' ? ' animate-spin' : ''}`)}Shuffle Picks</button><button class="w-full sm:w-auto px-space-md py-2 rounded-lg bg-primary text-on-primary hover:bg-primary-fixed font-label-md text-label-md font-semibold transition-all shadow-[0_0_12px_rgba(226,55,68,0.35)] flex items-center justify-center gap-1.5" data-act="share" type="button">${icon(S.copied ? 'check' : 'share', 'text-[16px]')}${S.copied ? 'Copied to clipboard' : 'Share Shortlist'}</button></div></div>` : ''}
<div class="my-space-md flex items-center justify-center gap-2 text-center">${icon('check_circle', 'text-[15px] text-tertiary')}<span class="font-caption text-caption text-on-surface-variant">All rankings drawn from the Zomato Bangalore restaurant dataset.</span></div>
</div></div></main>${footer(true)}${modalView(S)}`;
}

function modalView(S) {
  if (!S.modal) return '';
  const D = S.data, p = S.draft;
  const budget = D.budgets.find((b) => b.value === p.budget);
  const budgetBtns = D.budgets.map((b) => (b.value === p.budget
    ? `<button class="budget-btn py-1 px-1.5 rounded-lg text-center flex flex-col items-center justify-center bg-[#E23744] text-white shadow-[0_0_12px_rgba(226,55,68,0.4)] transition-all" data-act="pick-budget" data-value="${b.value}" type="button"><div class="flex items-center gap-1"><span class="font-label-sm text-[11px] font-semibold leading-tight">${h(b.label)}</span>${icon('check', 'text-[12px]')}</div><span class="text-[10px] text-white/90 leading-none whitespace-nowrap">${h(b.range)}</span></button>`
    : `<button class="budget-btn py-1 px-1.5 rounded-lg text-center flex flex-col items-center justify-center text-on-surface-variant hover:text-on-surface hover:bg-[#2A2A32] transition-all" data-act="pick-budget" data-value="${b.value}" type="button"><span class="font-label-sm text-[11px] font-semibold leading-tight">${h(b.label)}</span><span class="text-[10px] text-on-surface-variant leading-none whitespace-nowrap">${h(b.range)}</span></button>`)).join('');
  const options = D.locations.map((l) => `<option${l === p.location ? ' selected' : ''} value="${h(l)}">${h(l)}</option>`).join('');
  const tags = QUICK.map((t) => (p.extra.toLowerCase().includes(t.toLowerCase())
    ? `<button class="ambience-tag px-2.5 py-1 rounded-lg bg-primary-container/20 text-primary border border-primary-container/40 font-caption text-caption transition-colors flex items-center gap-1" data-act="toggle-extra" data-value="${h(t)}" type="button">${icon('check', 'text-[13px]')}${h(t)}</button>`
    : `<button class="ambience-tag px-2.5 py-1 rounded-lg bg-[#17171C] text-on-surface-variant hover:text-on-surface hover:bg-[#2A2A32] font-caption text-caption transition-colors border border-[#2A2A32]" data-act="toggle-extra" data-value="${h(t)}" type="button">+ ${h(t)}</button>`)).join('');
  const applying = S.loading === 'modal';
  return `<div class="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto transition-opacity duration-200" data-act="modal-backdrop">
<div class="relative w-full max-w-2xl bg-[#17171C] border border-[#2A2A32] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] my-auto transition-all transform duration-200" data-dialog role="dialog" aria-modal="true" aria-label="Edit Preferences">
<div class="px-6 py-5 border-b border-[#2A2A32] flex items-center justify-between gap-4 bg-[#17171C] shrink-0"><div><h2 class="font-bold text-xl text-[#F4F4F6] tracking-tight font-headline-md">Edit Preferences</h2><p class="text-xs text-[#A1A1AA] mt-0.5">Adjust your criteria to update recommendations in real-time</p></div><button aria-label="Close modal" class="text-[#A1A1AA] hover:text-[#F4F4F6] hover:bg-[#2A2A32] p-2 rounded-lg transition-colors flex items-center justify-center" data-act="close-modal" type="button"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M6 18L18 6M6 6l12 12" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg></button></div>
<div class="overflow-y-auto p-6 space-y-6 flex-1 text-on-surface">
<div class="space-y-3"><div class="flex items-center gap-2">${icon('pin_drop', 'text-[18px] text-primary')}<h3 class="font-headline-sm text-headline-sm text-on-surface font-semibold">Location &amp; Budget</h3></div><div class="grid grid-cols-1 md:grid-cols-2 gap-4 bg-[#1F1F26] p-4 rounded-xl border border-[#2A2A32]"><div class="space-y-1.5"><div class="flex items-center justify-between"><label class="font-label-md text-label-md text-on-surface flex items-center gap-1.5" for="modalLocationSelect">${icon('near_me', 'text-[16px] text-primary')}Location in Bangalore</label><span class="font-caption text-caption text-on-surface-variant">${h(D.stats.hubs)} food hubs</span></div><div class="relative"><select class="w-full h-11 bg-[#17171C] rounded-lg px-3 pr-8 text-sm text-on-surface border border-[#2A2A32] shadow-sm hover:border-primary/50 focus:border-primary outline-none transition-colors appearance-none cursor-pointer" id="modalLocationSelect" data-input="location">${options}</select>${icon('expand_more', 'text-on-surface-variant text-[18px] pointer-events-none absolute right-3 top-3')}</div><p class="font-caption text-caption text-on-surface-variant flex items-center gap-1 pt-1">${icon('bolt', 'text-[13px] text-tertiary')}Locality lookup covers micro-pubs, bistros, and iconic messes.</p></div><div class="space-y-1.5"><div class="flex items-center justify-between"><label class="font-label-md text-label-md text-on-surface flex items-center gap-1.5">${icon('payments', 'text-[16px] text-secondary')}Budget for Two</label><span class="font-caption text-caption px-2 py-0.5 rounded-full bg-secondary-container/20 text-secondary border border-secondary/30">${h(budget ? budget.range : '')}</span></div><div class="grid grid-cols-3 gap-1.5 bg-[#17171C] p-1 rounded-xl h-11 border border-[#2A2A32]">${budgetBtns}</div></div></div></div>
<div class="space-y-3"><div class="flex items-center justify-between"><div class="flex items-center gap-2">${icon('ramen_dining', 'text-[18px] text-tertiary')}<h3 class="font-headline-sm text-headline-sm text-on-surface font-semibold">Cuisine Profile</h3></div><span class="font-caption text-caption text-on-surface-variant">${h(D.cuisines.all.length)} cuisines</span></div><div class="bg-[#1F1F26] p-4 rounded-xl border border-[#2A2A32]">${cuisinePills(S, true)}</div></div>
<div class="space-y-3"><div class="flex items-center gap-2">${icon('tune', 'text-[18px] text-secondary')}<h3 class="font-headline-sm text-headline-sm text-on-surface font-semibold">Precision &amp; Criteria</h3></div><div class="grid grid-cols-1 md:grid-cols-2 gap-4">${sliderCard('rating', S, true)}${sliderCard('top_n', S, true)}</div></div>
<div class="space-y-3"><div class="flex items-center justify-between"><div class="flex items-center gap-2"><label class="font-headline-sm text-headline-sm text-on-surface flex items-center gap-1.5" for="modalPromptInput">${icon('psychology', 'text-[18px] text-primary')}Ambience &amp; Extra Preferences</label></div><span class="font-caption text-caption text-outline" data-out="count">${p.extra.length}/${D.max_extra}</span></div><div class="bg-[#1F1F26] p-4 rounded-xl border border-[#2A2A32] space-y-3"><div class="relative"><input class="w-full bg-[#17171C] rounded-xl px-4 py-2.5 text-on-surface font-body-md text-body-md border border-[#2A2A32] focus:border-primary/60 outline-none transition-all shadow-sm placeholder:text-outline" id="modalPromptInput" data-input="extra" maxlength="${D.max_extra}" placeholder="e.g. family-friendly, quick service, good for a date" type="text" value="${h(p.extra)}"></div><div class="flex flex-wrap gap-1.5">${tags}</div></div></div>
</div>
<div class="border-t border-[#2A2A32] bg-[#131316]/95 backdrop-blur px-6 py-4 flex items-center justify-between gap-4 shrink-0"><button class="text-xs text-[#A1A1AA] hover:text-[#F4F4F6] underline underline-offset-4 flex items-center gap-1.5 transition-colors" data-act="modal-defaults" type="button">${icon('restart_alt', 'text-[14px]')}Reset to Defaults</button><div class="flex items-center gap-3"><button class="px-5 py-2.5 rounded-xl border border-[#2A2A32] text-sm font-medium text-[#A1A1AA] hover:text-[#F4F4F6] hover:bg-[#1F1F26] transition-colors" data-act="close-modal" type="button">Cancel</button><button class="px-6 py-2.5 rounded-xl bg-[#E23744] hover:bg-[#d02e3b] text-white text-sm font-semibold shadow-lg shadow-[#E23744]/20 flex items-center gap-2 transition-all hover:scale-[1.02] active:scale-[0.98]" data-act="modal-apply" type="button"${applying ? ' disabled' : ''}>${applying ? `${icon('refresh', 'text-[18px] animate-spin')} Updating...` : `${icon('check', 'text-[18px]')}Apply Changes`}</button></div></div>
</div></div>`;
}

// ---------------------------------------------------------------------------------------------------------
// State, rendering and events
// ---------------------------------------------------------------------------------------------------------
function render(S) {
  const results = !!S.data.view;
  S.root.className = `rr-root bg-surface-container-lowest font-body-md text-body-md text-on-surface antialiased${results ? ' flex flex-col min-h-screen' : ''}`;
  S.root.innerHTML = results ? resultsView(S) : homeView(S);
}

function search(S, prefs, origin) {
  if (S.loading) return;
  S.loading = origin;
  S.error = false;
  S.dd = null;
  render(S);
  S.trigger('submit', { ...clone(prefs), nonce: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}` });
}

function onClick(S, e) {
  const el = e.target.closest('[data-act]');
  // Close open dropdowns when clicking anywhere outside them.
  if (S.dd && !e.target.closest(`[data-dd="${S.dd}"]`)) { S.dd = null; if (!el) { render(S); return; } }
  if (!el) return;
  const act = el.dataset.act, val = el.dataset.value;
  const D = S.data;
  switch (act) {
    case 'modal-backdrop':
      if (e.target.closest('[data-dialog]')) return;
      S.modal = false; S.draft = clone(S.chips); break;
    case 'toggle-location': S.dd = S.dd === 'location' ? null : 'location'; break;
    case 'toggle-cuisines': S.dd = S.dd === 'cuisine' ? null : 'cuisine'; break;
    case 'pick-location': S.draft.location = val; S.dd = null; break;
    case 'pick-budget': S.draft.budget = val; break;
    case 'pick-cuisine': S.draft.cuisine = val || null; S.dd = null; break;
    case 'add-extra': S.draft.extra = appendText(S.draft.extra, val, D.max_extra); break;
    case 'toggle-extra':
      S.draft.extra = S.draft.extra.toLowerCase().includes(val.toLowerCase()) ? removeText(S.draft.extra, val) : appendText(S.draft.extra, val, D.max_extra);
      break;
    case 'reset-form': S.draft = clone(D.defaults); S.dd = null; break;
    case 'reset-all': S.trigger('reset', Date.now()); return;
    case 'submit-home': e.preventDefault(); search(S, S.draft, 'home'); return;
    case 'open-modal': S.draft = clone(S.chips); S.modal = true; break;
    case 'close-modal': S.modal = false; S.dd = null; S.draft = clone(S.chips); break;
    case 'modal-defaults': S.draft = clone(D.defaults); break;
    case 'modal-apply': S.chips = clone(S.draft); search(S, S.draft, 'modal'); return;
    case 'chip-clear-extra': S.chips.extra = ''; break;
    case 'chip-add-extra': S.chips.extra = appendText(S.chips.extra, val, D.max_extra); break;
    case 'chip-apply': search(S, S.chips, 'chips'); return;
    case 'shuffle': search(S, D.prefs, 'shuffle'); return;
    case 'use-location': S.chips = { ...S.chips, location: val }; search(S, S.chips, 'chips'); return;
    case 'share': {
      const list = D.view.items.map((it) => `${it.rank}. ${it.name} (${it.location}) · ${it.cost}`).join('\n');
      const text = `My Bangalore restaurant shortlist:\n${list}`;
      (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject()).then(() => {
        S.copied = true; render(S);
        setTimeout(() => { S.copied = false; if (S.root.isConnected) render(S); }, 1800);
      }).catch(() => {});
      return;
    }
    default: return;
  }
  render(S);
  if (act === 'toggle-location' || act === 'toggle-cuisines') {
    const box = S.root.querySelector(`[data-filter="${S.dd}"]`);
    if (box) box.focus({ preventScroll: true });
  }
}

function onInput(S, e) {
  const t = e.target;
  if (t.dataset.filter) {
    const q = t.value.toLowerCase();
    S.root.querySelectorAll(`[data-list="${t.dataset.filter}"] [data-search]`).forEach((b) => {
      b.style.display = b.dataset.search.includes(q) ? 'flex' : 'none';
    });
    return;
  }
  const key = t.dataset.input;
  if (!key) return;
  const scope = t.closest('[data-dialog]') || S.root;
  if (key === 'min_rating') {
    S.draft.min_rating = parseFloat(t.value);
    scope.querySelector('[data-out="rating"]').textContent = fmtRating(t.value);
  } else if (key === 'top_n') {
    S.draft.top_n = parseInt(t.value, 10);
    scope.querySelector('[data-out="top_n"]').textContent = `${t.value} recommendations`;
  } else if (key === 'extra') {
    S.draft.extra = t.value;
    scope.querySelector('[data-out="count"]').textContent = `${t.value.length}/${S.data.max_extra}`;
  } else if (key === 'location') {
    S.draft.location = t.value;
  }
}

export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  ensureFonts();
  let S = parentElement.__rr;
  if (!S) {
    const root = document.createElement('div');
    parentElement.appendChild(root);
    S = parentElement.__rr = { root, served: undefined, loading: null, modal: false, dd: null, error: false, copied: false };
    root.addEventListener('click', (e) => onClick(S, e));
    root.addEventListener('input', (e) => onInput(S, e));
    root.addEventListener('change', (e) => onInput(S, e));
    root.addEventListener('submit', (e) => { e.preventDefault(); search(S, S.draft, 'home'); });
    root.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && e.target.dataset.input === 'extra' && !S.data.view) { e.preventDefault(); search(S, S.draft, 'home'); }
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && (S.modal || S.dd)) { S.modal = false; S.dd = null; S.draft = clone(S.chips); render(S); }
    });
  }
  S.data = data;
  S.trigger = setTriggerValue;
  // A new `served` id means Python finished a search (or reset): adopt its preferences and clear transient UI.
  if (data.served !== S.served) {
    const firstRender = S.served === undefined;
    S.served = data.served;
    S.chips = clone(data.prefs);
    S.draft = clone(data.prefs);
    S.loading = null;
    S.modal = false;
    S.dd = null;
    S.error = !!data.error;
    if (!firstRender && data.view) window.scrollTo?.(0, 0);
  }
  render(S);
}
