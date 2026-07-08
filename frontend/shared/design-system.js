/* FantaNostalgia Design System — Vanilla JS component library.
 * Porting 1:1 di `_ds_bundle.js` (React) — stessi props/varianti/stati,
 * nessuna dipendenza esterna. Ogni factory ritorna un HTMLElement pronto
 * per l'append. Richiede design-system.css per lo stile.
 */
(() => {
  const ns = (window.FantaNostalgiaDS = window.FantaNostalgiaDS || {});

  function appendChildren(parent, children) {
    if (children == null) return;
    const list = Array.isArray(children) ? children : [children];
    for (const child of list) {
      if (child == null) continue;
      parent.appendChild(child instanceof Node ? child : document.createTextNode(String(child)));
    }
  }

  /* ── Badge ──────────────────────────────────────────────────────── */
  function Badge({ children, variant = 'default' } = {}) {
    const el = document.createElement('span');
    el.className = `ds-badge ds-badge--${variant}`;
    appendChildren(el, children);
    return el;
  }

  /* ── Button ─────────────────────────────────────────────────────── */
  function Button({ children, variant = 'default', disabled = false, onClick, type = 'button', fullWidth = false } = {}) {
    const el = document.createElement('button');
    el.type = type;
    el.className = `ds-button ds-button--${variant}${fullWidth ? ' ds-button--full' : ''}`;
    el.disabled = disabled;
    appendChildren(el, children);
    if (onClick) el.addEventListener('click', onClick);
    return el;
  }

  /* ── Panel ──────────────────────────────────────────────────────── */
  function Panel({ children, title, variant = 'default' } = {}) {
    const el = document.createElement('div');
    el.className = `ds-panel ds-panel--${variant}`;
    if (title) {
      const h4 = document.createElement('h4');
      h4.className = 'ds-panel__title';
      h4.textContent = title;
      el.appendChild(h4);
    }
    appendChildren(el, children);
    return el;
  }

  /* ── Table ──────────────────────────────────────────────────────── */
  function Table({ columns = [], rows = [], onRowClick } = {}) {
    const wrap = document.createElement('div');
    wrap.className = 'ds-table-wrap';
    const table = document.createElement('table');
    table.className = 'ds-table';

    const thead = document.createElement('thead');
    const headRow = document.createElement('tr');
    columns.forEach((col) => {
      const th = document.createElement('th');
      th.textContent = col.label;
      th.style.textAlign = col.align || 'left';
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);

    const tbody = document.createElement('tbody');
    rows.forEach((row, ri) => {
      const cells = Array.isArray(row) ? row : row.cells || [];
      const tr = document.createElement('tr');
      tr.className = 'ds-table__row';
      if (onRowClick) {
        tr.classList.add('ds-table__row--clickable');
        tr.addEventListener('click', () => onRowClick(row, ri));
      }
      cells.forEach((cell, ci) => {
        const col = columns[ci] || {};
        const td = document.createElement('td');
        td.style.textAlign = col.align || 'left';
        if (col.pixel) td.classList.add('ds-table__cell--pixel');
        if (col.nowrap) td.classList.add('ds-table__cell--nowrap');
        if (col.color) td.style.color = col.color;
        appendChildren(td, cell);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

    table.appendChild(thead);
    table.appendChild(tbody);
    wrap.appendChild(table);
    return wrap;
  }

  /* ── EmptyState ─────────────────────────────────────────────────── */
  function EmptyState({ message, action, onAction } = {}) {
    const wrap = document.createElement('div');
    wrap.className = 'ds-empty-state';
    const msg = document.createElement('div');
    msg.className = 'ds-empty-state__message';
    msg.textContent = message;
    wrap.appendChild(msg);
    if (action && onAction) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ds-empty-state__action';
      btn.textContent = action;
      btn.addEventListener('click', onAction);
      wrap.appendChild(btn);
    }
    return wrap;
  }

  /* ── HelpBox ────────────────────────────────────────────────────── */
  function HelpBox({ title, children, link, linkText = 'Dettagli →', variant = 'info' } = {}) {
    const wrap = document.createElement('div');
    wrap.className = `ds-help-box ds-help-box--${variant}`;

    const icon = document.createElement('span');
    icon.className = 'ds-help-box__icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = 'i';
    wrap.appendChild(icon);

    const body = document.createElement('div');
    body.className = 'ds-help-box__body';
    if (title) {
      const strong = document.createElement('strong');
      strong.className = 'ds-help-box__title';
      strong.textContent = title;
      body.appendChild(strong);
    }
    const p = document.createElement('p');
    p.className = 'ds-help-box__text';
    appendChildren(p, children);
    body.appendChild(p);
    if (link) {
      const a = document.createElement('a');
      a.className = 'ds-help-box__link';
      a.href = link;
      a.textContent = linkText;
      body.appendChild(a);
    }
    wrap.appendChild(body);
    return wrap;
  }

  /* ── FileSpec ───────────────────────────────────────────────────── */
  function FileSpec({ format, structure, note } = {}) {
    const wrap = document.createElement('div');
    wrap.className = 'ds-file-spec';

    const header = document.createElement('div');
    header.className = 'ds-file-spec__header';
    const title = document.createElement('strong');
    title.className = 'ds-file-spec__title';
    title.textContent = 'Formato atteso';
    header.appendChild(title);
    if (format) {
      const badge = document.createElement('span');
      badge.className = 'ds-file-spec__format';
      badge.textContent = format;
      header.appendChild(badge);
    }
    wrap.appendChild(header);

    if (structure) {
      const p = document.createElement('p');
      p.className = 'ds-file-spec__structure';
      appendChildren(p, structure);
      wrap.appendChild(p);
    }
    if (note) {
      const p = document.createElement('p');
      p.className = 'ds-file-spec__note';
      appendChildren(p, note);
      wrap.appendChild(p);
    }
    return wrap;
  }

  /* ── Message ────────────────────────────────────────────────────── */
  function Message({ children, variant = 'ok', onDismiss } = {}) {
    const wrap = document.createElement('div');
    wrap.className = `ds-message ds-message--${variant}`;
    wrap.setAttribute('role', 'status');
    const span = document.createElement('span');
    appendChildren(span, children);
    wrap.appendChild(span);
    if (onDismiss) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ds-message__dismiss';
      btn.setAttribute('aria-label', 'Chiudi messaggio');
      btn.textContent = '×';
      btn.addEventListener('click', () => onDismiss(wrap));
      wrap.appendChild(btn);
    }
    wrap.dismiss = () => wrap.remove();
    return wrap;
  }

  /* ── ProgressBar ────────────────────────────────────────────────── */
  function ProgressBar({ value = 0, max = 100, label, showPercent = false } = {}) {
    const wrap = document.createElement('div');
    wrap.className = 'ds-progress-bar';

    let labelSpan = null;
    let pctSpan = null;
    if (label || showPercent) {
      const header = document.createElement('div');
      header.className = 'ds-progress-bar__header';
      if (label) {
        labelSpan = document.createElement('span');
        header.appendChild(labelSpan);
      }
      if (showPercent) {
        pctSpan = document.createElement('span');
        pctSpan.className = 'ds-progress-bar__percent';
        header.appendChild(pctSpan);
      }
      wrap.appendChild(header);
    }

    const track = document.createElement('div');
    track.className = 'ds-progress-bar__track';
    track.setAttribute('role', 'progressbar');
    track.setAttribute('aria-valuemin', '0');
    track.setAttribute('aria-valuemax', '100');
    const fill = document.createElement('div');
    fill.className = 'ds-progress-bar__fill';
    track.appendChild(fill);
    wrap.appendChild(track);

    function update(v, m = max) {
      const pct = Math.min(100, Math.max(0, m > 0 ? (v / m) * 100 : 0));
      fill.style.width = `${pct}%`;
      track.setAttribute('aria-valuenow', String(Math.round(pct)));
      if (labelSpan) labelSpan.textContent = label;
      if (pctSpan) pctSpan.textContent = `${Math.round(pct)}%`;
    }

    update(value, max);
    wrap.update = update;
    return wrap;
  }

  /* ── DropZone ───────────────────────────────────────────────────── */
  function DropZone({ onFile, accept, label = 'Trascina il file qui', sublabel, fileName } = {}) {
    const wrap = document.createElement('div');
    wrap.className = 'ds-dropzone';
    wrap.tabIndex = 0;
    wrap.setAttribute('role', 'button');

    const input = document.createElement('input');
    input.type = 'file';
    input.hidden = true;
    if (accept) input.accept = accept;

    const labelEl = document.createElement('div');
    labelEl.className = 'ds-dropzone__label';
    const subEl = document.createElement('div');
    subEl.className = 'ds-dropzone__sublabel';

    function setFile(confirmedName) {
      const confirmed = !!confirmedName;
      wrap.dataset.confirmed = String(confirmed);
      labelEl.textContent = confirmed ? `✓ ${confirmedName}` : label;
      const showSublabel = !!sublabel && !confirmed;
      subEl.textContent = showSublabel ? sublabel : '';
      subEl.hidden = !showSublabel;
    }

    wrap.appendChild(input);
    wrap.appendChild(labelEl);
    wrap.appendChild(subEl);
    setFile(fileName);

    wrap.addEventListener('click', () => input.click());
    wrap.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        input.click();
      }
    });
    wrap.addEventListener('dragover', (e) => {
      e.preventDefault();
      wrap.dataset.dragging = 'true';
    });
    wrap.addEventListener('dragleave', () => {
      wrap.dataset.dragging = 'false';
    });
    wrap.addEventListener('drop', (e) => {
      e.preventDefault();
      wrap.dataset.dragging = 'false';
      const file = e.dataTransfer.files && e.dataTransfer.files[0];
      if (file) {
        setFile(file.name);
        if (onFile) onFile(file);
      }
    });
    input.addEventListener('change', (e) => {
      const file = e.target.files && e.target.files[0];
      if (file) {
        setFile(file.name);
        if (onFile) onFile(file);
      }
    });

    wrap.setFile = setFile;
    return wrap;
  }

  /* ── Input ──────────────────────────────────────────────────────── */
  function Input({ label, id, type = 'text', placeholder, value, onChange, disabled = false, error, helpText, required = false } = {}) {
    const wrap = document.createElement('div');
    wrap.className = 'ds-input-wrap';

    if (label) {
      const lbl = document.createElement('label');
      lbl.className = 'ds-input__label';
      if (id) lbl.htmlFor = id;
      lbl.append(label);
      if (required) {
        const star = document.createElement('span');
        star.className = 'ds-input__required';
        star.textContent = '*';
        lbl.appendChild(star);
      }
      wrap.appendChild(lbl);
    }

    const input = document.createElement('input');
    input.className = 'ds-input';
    if (id) input.id = id;
    input.type = type;
    if (placeholder) input.placeholder = placeholder;
    if (value != null) input.value = value;
    input.disabled = disabled;
    input.required = required;
    if (onChange) input.addEventListener('input', onChange);
    wrap.appendChild(input);

    const errorId = id ? `${id}-error` : undefined;
    const helpId = id ? `${id}-help` : undefined;
    const errorEl = document.createElement('span');
    errorEl.className = 'ds-input__error';
    if (errorId) errorEl.id = errorId;
    const helpEl = document.createElement('span');
    helpEl.className = 'ds-input__help';
    if (helpId) helpEl.id = helpId;
    if (helpText) helpEl.textContent = helpText;
    wrap.appendChild(errorEl);
    wrap.appendChild(helpEl);

    function setError(msg) {
      if (msg) {
        input.dataset.error = 'true';
        input.setAttribute('aria-invalid', 'true');
        if (errorId) input.setAttribute('aria-describedby', errorId);
        errorEl.textContent = msg;
        errorEl.hidden = false;
        helpEl.hidden = true;
      } else {
        delete input.dataset.error;
        input.removeAttribute('aria-invalid');
        if (helpId) input.setAttribute('aria-describedby', helpId);
        else input.removeAttribute('aria-describedby');
        errorEl.hidden = true;
        helpEl.hidden = !helpText;
      }
    }
    setError(error);

    wrap.input = input;
    wrap.setError = setError;
    return wrap;
  }

  /* ── WizardSteps ────────────────────────────────────────────────── */
  function WizardSteps({ steps = [], current = 1, onNavigate } = {}) {
    const wrap = document.createElement('div');
    wrap.className = 'ds-wizard-steps';
    wrap.setAttribute('role', 'navigation');
    wrap.setAttribute('aria-label', 'Passaggi');

    const stepEls = steps.map((label, i) => {
      const num = i + 1;
      const stepEl = document.createElement('div');
      stepEl.className = 'ds-wizard-steps__step';
      stepEl.textContent = `${num} — ${label}`;
      if (onNavigate) {
        stepEl.classList.add('ds-wizard-steps__step--clickable');
        stepEl.tabIndex = 0;
        stepEl.setAttribute('role', 'button');
        stepEl.addEventListener('click', () => {
          if (stepEl.dataset.state !== 'active') onNavigate(num);
        });
        stepEl.addEventListener('keydown', (e) => {
          if ((e.key === 'Enter' || e.key === ' ') && stepEl.dataset.state !== 'active') {
            e.preventDefault();
            onNavigate(num);
          }
        });
      }
      wrap.appendChild(stepEl);
      return stepEl;
    });

    function setCurrent(activeNum) {
      stepEls.forEach((stepEl, i) => {
        const num = i + 1;
        const state = num < activeNum ? 'done' : num === activeNum ? 'active' : 'pending';
        stepEl.dataset.state = state;
        if (state === 'active') stepEl.setAttribute('aria-current', 'step');
        else stepEl.removeAttribute('aria-current');
      });
    }
    setCurrent(current);

    wrap.setCurrent = setCurrent;
    return wrap;
  }

  /* ── Tabs ───────────────────────────────────────────────────────── */
  function Tabs({ tabs = [], defaultTab, children } = {}) {
    const wrap = document.createElement('div');
    wrap.className = 'ds-tabs';

    const nav = document.createElement('div');
    nav.className = 'ds-tabs__nav';
    nav.setAttribute('role', 'tablist');

    const panel = document.createElement('div');
    panel.className = 'ds-tabs__panel';
    panel.setAttribute('role', 'tabpanel');

    let active = defaultTab || (tabs[0] && tabs[0].id) || '';
    const tabButtons = {};

    function renderPanel() {
      panel.innerHTML = '';
      const content = typeof children === 'function' ? children(active) : children;
      appendChildren(panel, content);
    }

    function setActive(id) {
      active = id;
      Object.entries(tabButtons).forEach(([tabId, btn]) => {
        btn.setAttribute('aria-selected', String(tabId === active));
      });
      renderPanel();
    }

    tabs.forEach((tab) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ds-tabs__tab';
      btn.textContent = tab.label;
      btn.setAttribute('role', 'tab');
      btn.setAttribute('aria-selected', String(tab.id === active));
      btn.addEventListener('click', () => setActive(tab.id));
      tabButtons[tab.id] = btn;
      nav.appendChild(btn);
    });

    wrap.appendChild(nav);
    wrap.appendChild(panel);
    renderPanel();

    wrap.setActive = setActive;
    return wrap;
  }

  /* ── Modal ──────────────────────────────────────────────────────── */
  function Modal({ open = false, title, children, onClose, actions } = {}) {
    const overlay = document.createElement('div');
    overlay.className = 'ds-modal-overlay';
    overlay.hidden = !open;

    const box = document.createElement('div');
    box.className = 'ds-modal';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-modal', 'true');
    box.tabIndex = -1;

    if (title) {
      const h3 = document.createElement('h3');
      h3.className = 'ds-modal__title';
      h3.textContent = title;
      box.appendChild(h3);
      box.setAttribute('aria-labelledby', '');
    }
    const body = document.createElement('div');
    body.className = 'ds-modal__body';
    appendChildren(body, children);
    box.appendChild(body);
    if (actions) {
      const actionsWrap = document.createElement('div');
      actionsWrap.className = 'ds-modal__actions';
      appendChildren(actionsWrap, actions);
      box.appendChild(actionsWrap);
    }
    overlay.appendChild(box);

    function close() {
      overlay.hidden = true;
      if (onClose) onClose();
    }
    function show() {
      overlay.hidden = false;
      box.focus();
    }

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) close();
    });
    overlay.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') close();
    });

    overlay.open = show;
    overlay.close = close;
    return overlay;
  }

  /* ── Confirm Dialog ─────────────────────────────────────────────── */
  function confirmDialog({ title, message, consequence, confirmLabel = 'Conferma', cancelLabel = 'Annulla', danger = true } = {}) {
    return new Promise((resolve) => {
      const msgEl = document.createElement('p');
      msgEl.className = 'ds-confirm-dialog__message';
      appendChildren(msgEl, message);
      const bodyChildren = [msgEl];
      if (consequence) {
        const warnEl = document.createElement('p');
        warnEl.className = 'ds-confirm-dialog__consequence';
        appendChildren(warnEl, consequence);
        bodyChildren.push(warnEl);
      }

      let settled = false;
      function finish(result) {
        if (settled) return;
        settled = true;
        overlay.remove();
        resolve(result);
      }

      const cancelBtn = Button({ children: cancelLabel, variant: 'secondary', onClick: () => overlay.close() });
      const confirmBtn = Button({ children: confirmLabel, variant: danger ? 'danger' : 'default', onClick: () => finish(true) });

      const overlay = Modal({
        title,
        children: bodyChildren,
        onClose: () => finish(false),
        actions: [cancelBtn, confirmBtn],
      });
      overlay.classList.add('ds-confirm-dialog');
      if (danger) overlay.classList.add('ds-confirm-dialog--danger');
      document.body.appendChild(overlay);
      overlay.open();
    });
  }

  Object.assign(ns, {
    Badge,
    Button,
    Panel,
    Table,
    EmptyState,
    HelpBox,
    FileSpec,
    Message,
    ProgressBar,
    DropZone,
    Input,
    WizardSteps,
    Tabs,
    Modal,
    confirmDialog,
  });
})();
