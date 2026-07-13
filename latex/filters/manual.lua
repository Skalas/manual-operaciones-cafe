-- manual.lua — filtro pandoc que adapta el contenido web del manual a LaTeX.
--
-- Trabaja sobre el AST de pandoc (no sobre texto), por lo que sobrevive a
-- cambios de formato en las páginas. Se aplica en dos pasadas:
--
--   1. Reconstrucción de listas HTML: el lector de markdown deja los <li> de
--      las listas con clase (ul.do, ul.timeline) como RawBlocks sueltos con el
--      texto entre ellos; aquí se reagrupan en BulletLists reales.
--   2. Componentes y limpieza: admonitions -> admonitionbox (tcolorbox),
--      spec/kpi/chips -> equivalentes imprimibles, fuera lo que no tiene
--      sentido en papel (mermaid, botones, navegación, barras decorativas)
--      y sustitución de caracteres sin glifo (☐, │) y campos en blanco.

local stringify = pandoc.utils.stringify

-- Títulos y colores por defecto de los admonitions (mismos del sitio).
local ADM_TITLE = {
  danger = "Prohibido", warning = "Importante", info = "Nota",
  note = "Nota", tip = "Recomendación", quote = "Detalle", success = "Hacer",
}
local ADM_COLOR = {
  danger = "AdmDanger", warning = "AdmWarning", info = "AdmInfo",
  note = "AdmInfo", tip = "AdmTip", quote = "AdmInfo", success = "AdmTip",
}

local function latex_escape(s)
  return (s:gsub("[%%&#_{}$]", "\\%0"))
end

-- ===========================================================================
-- Pasada 1: reagrupar listas HTML sueltas en BulletLists
-- ===========================================================================

-- ¿Con qué etiqueta abre este RawBlock html? ("li", "/ul", "p", …)
local function html_tag(raw)
  return raw.text:match("^%s*<%s*(/?%w+)")
end

-- Un <li>…</li> completo en una sola línea (timeline): parsear y extraer el item.
local function parse_full_li(text)
  local ok, doc = pcall(pandoc.read, text, "html")
  if not ok then return nil end
  for _, b in ipairs(doc.blocks) do
    if b.t == "BulletList" and #b.content > 0 then return b.content[1] end
  end
  return nil
end

local function regroup_html_lists(blocks)
  local out = pandoc.Blocks{}
  local items = nil      -- items acumulados de la lista en curso
  local current = nil    -- bloques del item abierto

  local function flush_list()
    if items and #items > 0 then out:insert(pandoc.BulletList(items)) end
    items, current = nil, nil
  end

  for _, b in ipairs(blocks) do
    local handled = false
    if b.t == "RawBlock" and b.format == "html" then
      local tag = html_tag(b)
      if tag == "ul" or tag == "ol" then
        items = items or pandoc.List{}
        handled = true
      elseif tag == "/ul" or tag == "/ol" then
        flush_list()
        handled = true
      elseif tag == "li" then
        items = items or pandoc.List{}
        if b.text:match("</li>") then                -- item completo en una línea
          local item = parse_full_li(b.text)
          if item then items:insert(item) end
          current = nil
        else                                          -- etiqueta suelta: abre item
          current = pandoc.Blocks{}
        end
        handled = true
      elseif tag == "/li" then
        if current then
          items:insert(current)
          current = nil
        end
        handled = true
      end
    end
    if not handled then
      if current then
        current:insert(b)
      else
        if items then flush_list() end
        out:insert(b)
      end
    end
  end
  flush_list()
  return out
end

-- ===========================================================================
-- Pasada 2: componentes e inlines
-- ===========================================================================

local function fix_str(el)
  local t = el.text
  if t:find("☐", 1, true) then
    local escaped = latex_escape(t:gsub("☐", "\1")):gsub("\1", "\\ensuremath{\\square}")
    return pandoc.RawInline("latex", escaped)
  end
  if t:find("│", 1, true) then
    return pandoc.Str((t:gsub("│", "|")))
  end
  if t:match("^___+$") then  -- campo para llenar a mano (la longitud marca el ancho)
    local w = math.min(utf8.len(t) * 0.35, 4.5)
    return pandoc.RawInline("latex", string.format("\\rule[-1pt]{%.1fcm}{0.4pt}", w))
  end
  return nil
end

local function fix_link(el)
  if el.classes:includes("md-button") then
    return {}                                    -- botones de descarga del sitio
  end
  local tgt = el.target
  if tgt:match("%.md$") or tgt:match("%.md#") or tgt:match("^#")
      or tgt:match("^descargas/") then
    return el.content                            -- enlace interno: queda el texto
  end
  return nil
end

local function fix_span(el)
  if el.classes:includes("t-title") then         -- hito del timeline
    return pandoc.Inlines{pandoc.Strong(el.content), pandoc.Str(" —")}
  end
  if el.classes:includes("t-goal") then          -- meta del hito, en cursiva
    return pandoc.Inlines{pandoc.Emph(el.content)}
  end
  if el.classes:includes("tag") then             -- etiqueta de nivel en encabezados
    local inl = pandoc.Inlines{pandoc.Str("(")}
    inl:extend(el.content)
    inl:insert(pandoc.Str(")"))
    return inl
  end
  return el.content                              -- chips, badges, value…: solo el texto
end

-- Si el lector convirtió HTML indentado en CodeBlock, reinterpretarlo como HTML.
local function html_from_codeblocks(content)
  local blocks = pandoc.Blocks{}
  for _, b in ipairs(content) do
    if b.t == "CodeBlock" and b.text:match("^%s*<") then
      local ok, doc = pcall(pandoc.read, b.text, "html")
      if ok then blocks:extend(doc.blocks) end
    else
      blocks:insert(b)
    end
  end
  return blocks
end

-- .spec: {label, value, unit} -> "Etiqueta: **valor** unidad"
local function spec_line(spec)
  local label, value, unit
  spec:walk({
    Span = function(s)
      if s.classes:includes("value") then value = stringify(s)
      elseif s.classes:includes("unit") then unit = stringify(s)
      elseif s.classes:includes("label") then label = stringify(s) end
    end,
  })
  if not label then
    -- <p class="label"> pierde la clase: la etiqueta es el primer bloque sin valor
    for _, b in ipairs(spec.content) do
      if (b.t == "Plain" or b.t == "Para") and not stringify(b):find(value or "\1", 1, true) then
        label = stringify(b)
        break
      end
    end
  end
  local inl = pandoc.Inlines{}
  inl:insert(pandoc.Str((label or "") .. ": "))
  inl:insert(pandoc.Strong{pandoc.Str(value or "")})
  if unit and unit ~= "" then inl:insert(pandoc.Str(" " .. unit)) end
  return inl
end

-- .kpi -> "**Nombre** — fórmula · Meta: **valor**"
local function kpi_block(div)
  local name, formula, target
  for _, b in ipairs(html_from_codeblocks(div.content)) do
    local cls = (b.t == "Div") and b.classes or pandoc.List{}
    if cls:includes("k-target") then
      target = stringify(b):gsub("%s*meta%s*$", "")
    elseif cls:includes("k-bar") then
      -- barra decorativa: fuera
    elseif cls:includes("k-name") then
      name = stringify(b)
    elseif cls:includes("k-formula") then
      formula = stringify(b)
    elseif b.t == "Para" or b.t == "Plain" then
      -- <p class="k-name"> / <p class="k-formula"> pierden la clase:
      -- el primero es el nombre, el segundo la fórmula.
      if not name then name = stringify(b)
      elseif not formula then formula = stringify(b) end
    end
  end
  local inl = pandoc.Inlines{pandoc.Strong{pandoc.Str(name or "")}}
  if formula and formula ~= "" then
    inl:insert(pandoc.Str(" — "))
    inl:insert(pandoc.Emph{pandoc.Str(formula)})
  end
  if target and target ~= "" then
    inl:insert(pandoc.Str(" · Meta: "))
    inl:insert(pandoc.Strong{pandoc.Str(target)})
  end
  return pandoc.Para(inl)
end

-- Transforma un Div según su clase. Los Div anidados ya llegan transformados
-- (pandoc procesa de adentro hacia afuera), por eso los contenedores (spec-grid,
-- kpi-grid…) solo desenvuelven su contenido.
local function render_div(div)
  local cls = div.classes

  if cls:includes("admonition") then
    local kind = "info"
    for k in pairs(ADM_TITLE) do if cls:includes(k) then kind = k end end
    local title = div.attributes["title"] or ADM_TITLE[kind]
    local blocks = pandoc.Blocks{}
    blocks:insert(pandoc.RawBlock("latex",
      string.format("\\begin{admonitionbox}{%s}{%s}", ADM_COLOR[kind], latex_escape(title))))
    blocks:extend(div.content)
    blocks:insert(pandoc.RawBlock("latex", "\\end{admonitionbox}"))
    return blocks
  end

  -- Columnas del bloque do/don't: cada una es una caja apilada en el PDF.
  if cls:includes("dd-do") or cls:includes("dd-dont") then
    local color, title = "AdmTip", "Hacer"
    if cls:includes("dd-dont") then color, title = "AdmDanger", "Evitar" end
    local blocks = pandoc.Blocks{}
    blocks:insert(pandoc.RawBlock("latex",
      string.format("\\begin{admonitionbox}{%s}{%s}", color, title)))
    blocks:extend(div.content)
    blocks:insert(pandoc.RawBlock("latex", "\\end{admonitionbox}"))
    return blocks
  end

  if cls:includes("spec") then
    return { pandoc.LineBlock{spec_line(div)} }
  end

  if cls:includes("kpi") then
    return { kpi_block(div) }
  end

  if cls:includes("chips") then
    local inl = pandoc.Inlines{}
    div:walk({ Span = function(s)
      if #inl > 0 then inl:insert(pandoc.Str("  ·  ")) end
      inl:insert(pandoc.Emph(s.content))
    end })
    if #inl == 0 then inl:insert(pandoc.Emph{pandoc.Str(stringify(div))}) end
    return { pandoc.Para(inl) }
  end

  if cls:includes("k-bar") then return {} end

  -- Contenedores y decoración (hero, grid, cards, severity, sev, spec-grid,
  -- kpi-grid, quote…): se queda solo el contenido.
  return div.content
end

-- La extracción de componentes (pasada de Div) debe correr ANTES que la
-- limpieza de inlines: dentro de una misma pasada pandoc procesa primero a
-- los hijos, y desenvolver los Span borraría las clases (value, k-name…)
-- que spec_line/kpi_block necesitan leer.
local pass_cleanup = {
  Str = fix_str,
  Link = fix_link,
  Span = fix_span,

  RawInline = function(el)
    if el.format == "html" then return {} end    -- <small>, </p>… sueltos en línea
    return nil
  end,

  CodeBlock = function(el)
    if el.classes:includes("mermaid") then return {} end
    return nil
  end,

  HorizontalRule = function()
    return {}                                    -- separadores temáticos del sitio
  end,

  RawBlock = function(el)
    if el.format == "html" then return {} end    -- etiquetas residuales (<p>, <details>…)
    return nil
  end,

  Para = function(el)
    if #el.content == 0 then return {} end
    local first = el.content[1]
    if first and first.t == "Str" and first.text:sub(1, 3) == "⬇" then
      return {}                                  -- líneas de descarga
    end
    return nil
  end,
}

return {
  { Blocks = regroup_html_lists },
  { Div = render_div },
  pass_cleanup,
}
