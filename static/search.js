// static/search.js - bÃºsqueda en el navegador. Vainilla ES6+, sin dependencias.
// Estilo funcional: funciones puras arriba; el DOM (efectos) solo al final.
//
// MDN:
//   fetch                 https://developer.mozilla.org/es/docs/Web/API/Fetch_API
//   Array.filter / every  https://developer.mozilla.org/es/docs/Web/JavaScript/Reference/Global_Objects/Array/filter
//   String.normalize      https://developer.mozilla.org/es/docs/Web/JavaScript/Reference/Global_Objects/String/normalize
//   Element.replaceChildren https://developer.mozilla.org/es/docs/Web/API/Element/replaceChildren
//   Escapes Unicode \p{M} https://developer.mozilla.org/es/docs/Web/JavaScript/Reference/Regular_expressions/Unicode_character_class_escape

// --- puras ------------------------------------------------------------------

// "Ã¡rbol" â†’ "arbol": minÃºsculas y sin acentos
const normalize = s => (s || "").toLowerCase().normalize("NFD").replace(/\p{M}/gu, "");

const terms = query => normalize(query).split(/\s+/).filter(Boolean);

const haystack = post => normalize(`${post.title} ${(post.tags || []).join(" ")} ${post.text}`);

// Un post coincide si contiene TODOS los tÃ©rminos
const matches = ts => post => ts.every(t => haystack(post).includes(t));

// Cuenta cuÃ¡ntas veces aparece un tÃ©rmino dentro de una cadena
const countOccurrences = (str, term) => {
  if (!term || !str) return 0;
  let count = 0, pos = 0;
  while ((pos = str.indexOf(term, pos)) !== -1) {
    count++;
    pos += term.length;
  }
  return count;
};

// PuntuaciÃ³n de relevancia: mayor peso al tÃ­tulo (x3) y etiquetas (x2) que al cuerpo (x1) (Ejercicio 4)
const score = ts => post => {
  const normTitle = normalize(post.title);
  const normTags = normalize((post.tags || []).join(" "));
  const normText = normalize(post.text);

  return ts.reduce((acc, t) => {
    return acc + (countOccurrences(normTitle, t) * 3)
               + (countOccurrences(normTags, t) * 2)
               + countOccurrences(normText, t);
  }, 0);
};

// BÃºsqueda pura: filtra coincidencias y ordena descendentemente por relevancia
const search = (posts, query) => {
  const ts = terms(query);
  if (!ts.length) return [];

  return posts
    .filter(matches(ts))
    .map(p => ({ post: p, points: score(ts)(p) }))
    .sort((a, b) => b.points - a.points)
    .map(item => item.post);
};

// --- efectos (DOM) ----------------------------------------------------------

// textContent, nunca innerHTML: el contenido se trata como texto, no como HTML
const toItem = base => post => {
  const a = document.createElement("a");
  a.href = base.replace(/\/$/, "") + post.url;
  a.textContent = post.title;

  const meta = document.createElement("span");
  meta.className = "meta";
  meta.textContent = ` ${post.date.slice(0, 10)} - ${post.summary}`;

  const li = document.createElement("li");
  li.append(a, meta);
  return li;
};

const emptyItem = () => {
  const li = document.createElement("li");
  li.className = "meta";
  li.textContent = "Sin resultados.";
  return li;
};

const main = async () => {
  const input = document.querySelector("#q");
  const list = document.querySelector("#results");
  if (!input || !list) return;

  const { index, base } = list.dataset;
  const posts = await fetch(index).then(r => r.json());

  input.addEventListener("input", () => {
    const found = search(posts, input.value);
    const items = found.map(toItem(base));
    list.replaceChildren(...(items.length || !input.value.trim() ? items : [emptyItem()]));
  });
};

main().catch(err => console.error("search.js:", err));