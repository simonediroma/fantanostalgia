/* @ds-bundle: {"format":3,"namespace":"FantaNostalgiaDesignSystem_90de16","components":[{"name":"Badge","sourcePath":"components/core/Badge.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Panel","sourcePath":"components/core/Panel.jsx"},{"name":"Table","sourcePath":"components/data/Table.jsx"},{"name":"EmptyState","sourcePath":"components/feedback/EmptyState.jsx"},{"name":"HelpBox","sourcePath":"components/feedback/HelpBox.jsx"},{"name":"Message","sourcePath":"components/feedback/Message.jsx"},{"name":"ProgressBar","sourcePath":"components/feedback/ProgressBar.jsx"},{"name":"DropZone","sourcePath":"components/forms/DropZone.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"WizardSteps","sourcePath":"components/forms/WizardSteps.jsx"},{"name":"Tabs","sourcePath":"components/navigation/Tabs.jsx"},{"name":"Modal","sourcePath":"components/overlay/Modal.jsx"}],"sourceHashes":{"components/core/Badge.jsx":"20abc752f30c","components/core/Button.jsx":"ad942391c142","components/core/Panel.jsx":"97d19a79393c","components/data/Table.jsx":"e73b2e8c3954","components/feedback/EmptyState.jsx":"296c9957ae8b","components/feedback/HelpBox.jsx":"c9ed4a0c8d4e","components/feedback/Message.jsx":"a3f6b216f5b9","components/feedback/ProgressBar.jsx":"79fda7c9e1b7","components/forms/DropZone.jsx":"03bdfed2c5a1","components/forms/Input.jsx":"a140a8cccd59","components/forms/WizardSteps.jsx":"6c3aca8ede15","components/navigation/Tabs.jsx":"d0bdda72a894","components/overlay/Modal.jsx":"b673ecada536"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.FantaNostalgiaDesignSystem_90de16 = window.FantaNostalgiaDesignSystem_90de16 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/core/Badge.jsx
try { (() => {
function Badge({
  children,
  variant = 'default'
}) {
  const variants = {
    default: {
      background: 'var(--border)',
      color: 'var(--muted)'
    },
    accent: {
      background: 'var(--accent)',
      color: 'var(--bg)'
    },
    cyan: {
      background: 'var(--accent2)',
      color: 'var(--bg)'
    },
    green: {
      background: 'var(--green)',
      color: '#000'
    },
    red: {
      background: 'var(--red)',
      color: '#fff'
    },
    outline: {
      background: 'transparent',
      color: 'var(--accent)',
      border: '1px solid var(--accent)'
    }
  };
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-block',
      fontFamily: 'var(--font-pixel)',
      fontSize: 'var(--fs-pixel-xs)',
      textTransform: 'uppercase',
      letterSpacing: '0.06em',
      padding: '2px 6px',
      verticalAlign: 'middle',
      lineHeight: 1.6,
      ...(variants[variant] ?? variants.default)
    }
  }, children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Badge.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
function Button({
  children,
  variant = 'default',
  disabled = false,
  onClick,
  type = 'button',
  fullWidth = false
}) {
  const [hovered, setHovered] = React.useState(false);
  const on = hovered && !disabled;
  const base = {
    fontFamily: 'var(--font-pixel)',
    fontSize: '0.6rem',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    border: '2px solid',
    boxShadow: disabled ? 'none' : 'var(--shadow-sm)',
    cursor: disabled ? 'default' : 'pointer',
    padding: '0.4rem 1rem',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.35rem',
    whiteSpace: 'nowrap',
    opacity: disabled ? 0.45 : 1,
    lineHeight: 1.5,
    width: fullWidth ? '100%' : undefined,
    justifyContent: fullWidth ? 'center' : undefined
  };
  const variants = {
    default: {
      background: on ? 'var(--accent2)' : 'var(--accent)',
      borderColor: on ? 'var(--accent2)' : 'var(--accent)',
      color: 'var(--bg)'
    },
    secondary: {
      background: on ? 'var(--accent)' : 'transparent',
      borderColor: 'var(--accent)',
      color: on ? 'var(--bg)' : 'var(--accent)'
    },
    danger: {
      background: 'var(--red)',
      borderColor: 'var(--red)',
      color: '#fff',
      opacity: disabled ? 0.45 : on ? 0.85 : 1
    },
    ghost: {
      background: 'transparent',
      borderColor: on ? 'var(--accent)' : 'var(--muted)',
      color: on ? 'var(--accent)' : 'var(--muted)'
    }
  };
  return /*#__PURE__*/React.createElement("button", {
    type: type,
    disabled: disabled,
    onClick: onClick,
    style: {
      ...base,
      ...(variants[variant] ?? variants.default)
    },
    onMouseEnter: () => setHovered(true),
    onMouseLeave: () => setHovered(false)
  }, children);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/Panel.jsx
try { (() => {
function Panel({
  children,
  title,
  variant = 'default'
}) {
  const variants = {
    default: {
      border: '2px solid var(--border)',
      boxShadow: 'var(--shadow-md)'
    },
    accent: {
      border: '2px solid var(--accent)',
      boxShadow: 'var(--shadow-accent)'
    },
    danger: {
      border: '2px solid var(--red)',
      boxShadow: 'var(--shadow-md)'
    },
    plain: {
      border: '1px solid var(--border)',
      boxShadow: 'none'
    }
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--surface)',
      padding: 'var(--space-5)',
      marginBottom: 'var(--space-4)',
      ...(variants[variant] ?? variants.default)
    }
  }, title && /*#__PURE__*/React.createElement("h4", {
    style: {
      fontFamily: 'var(--font-pixel)',
      fontSize: 'var(--fs-pixel-md)',
      color: 'var(--accent)',
      textTransform: 'uppercase',
      letterSpacing: '0.05em',
      marginBottom: 'var(--space-3)'
    }
  }, title), children);
}
Object.assign(__ds_scope, { Panel });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Panel.jsx", error: String((e && e.message) || e) }); }

// components/data/Table.jsx
try { (() => {
function TableRow({
  cells,
  columns,
  onRowClick,
  rowData,
  index
}) {
  const [hovered, setHovered] = React.useState(false);
  return /*#__PURE__*/React.createElement("tr", {
    onClick: onRowClick ? () => onRowClick(rowData, index) : undefined,
    style: {
      cursor: onRowClick ? 'pointer' : 'default',
      background: hovered ? 'rgba(255,230,0,0.07)' : 'transparent',
      borderBottom: '1px solid var(--border)'
    },
    onMouseEnter: () => setHovered(true),
    onMouseLeave: () => setHovered(false)
  }, cells.map((cell, ci) => {
    const col = columns[ci] || {};
    return /*#__PURE__*/React.createElement("td", {
      key: ci,
      style: {
        padding: '0.5rem 0.75rem',
        verticalAlign: 'middle',
        border: '1px solid var(--border)',
        color: col.color || undefined,
        fontFamily: col.pixel ? 'var(--font-pixel)' : 'var(--font-data)',
        fontSize: col.pixel ? 'var(--fs-pixel-xs)' : undefined,
        textAlign: col.align || 'left',
        whiteSpace: col.nowrap ? 'nowrap' : undefined
      }
    }, cell);
  }));
}
function Table({
  columns = [],
  rows = [],
  onRowClick
}) {
  const cellsFor = row => Array.isArray(row) ? row : row.cells || [];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      overflowX: 'auto'
    }
  }, /*#__PURE__*/React.createElement("table", {
    style: {
      width: '100%',
      borderCollapse: 'collapse',
      border: '2px solid var(--border)',
      fontFamily: 'var(--font-data)',
      fontSize: 'var(--fs-data-md)'
    }
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, columns.map((col, i) => /*#__PURE__*/React.createElement("th", {
    key: i,
    style: {
      background: 'var(--accent)',
      color: 'var(--bg)',
      fontFamily: 'var(--font-pixel)',
      fontSize: 'var(--fs-pixel-sm)',
      letterSpacing: '0.06em',
      padding: '0.5rem 0.75rem',
      textAlign: col.align || 'left',
      textTransform: 'uppercase',
      whiteSpace: 'nowrap',
      border: '1px solid var(--bg)'
    }
  }, col.label)))), /*#__PURE__*/React.createElement("tbody", null, rows.map((row, ri) => /*#__PURE__*/React.createElement(TableRow, {
    key: ri,
    cells: cellsFor(row),
    columns: columns,
    onRowClick: onRowClick,
    rowData: row,
    index: ri
  })))));
}
Object.assign(__ds_scope, { Table });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/Table.jsx", error: String((e && e.message) || e) }); }

// components/feedback/EmptyState.jsx
try { (() => {
function EmptyState({
  message,
  action,
  onAction
}) {
  const [hovered, setHovered] = React.useState(false);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'center',
      padding: 'var(--space-8) var(--space-4)',
      color: 'var(--muted)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-pixel)',
      fontSize: 'var(--fs-pixel-sm)',
      textTransform: 'uppercase',
      marginBottom: action ? 'var(--space-4)' : 0,
      lineHeight: 1.8
    }
  }, message), action && onAction && /*#__PURE__*/React.createElement("button", {
    onClick: onAction,
    style: {
      fontFamily: 'var(--font-pixel)',
      fontSize: 'var(--fs-pixel-xs)',
      textTransform: 'uppercase',
      background: 'transparent',
      border: `2px solid ${hovered ? 'var(--accent)' : 'var(--muted)'}`,
      color: hovered ? 'var(--accent)' : 'var(--muted)',
      padding: 'var(--space-2) var(--space-4)',
      cursor: 'pointer',
      boxShadow: 'var(--shadow-sm)'
    },
    onMouseEnter: () => setHovered(true),
    onMouseLeave: () => setHovered(false)
  }, action));
}
Object.assign(__ds_scope, { EmptyState });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/EmptyState.jsx", error: String((e && e.message) || e) }); }

// components/feedback/HelpBox.jsx
try { (() => {
function HelpBox({
  title,
  children,
  link,
  linkText = 'Dettagli →',
  variant = 'info'
}) {
  const variants = {
    info: {
      borderColor: 'var(--accent2)',
      iconBg: 'var(--accent2)',
      iconColor: 'var(--bg)'
    },
    warn: {
      borderColor: 'var(--accent)',
      iconBg: 'var(--accent)',
      iconColor: 'var(--bg)'
    },
    danger: {
      borderColor: 'var(--red)',
      iconBg: 'var(--red)',
      iconColor: '#fff'
    }
  };
  const v = variants[variant] ?? variants.info;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 'var(--space-3)',
      background: 'var(--surface)',
      border: `2px solid ${v.borderColor}`,
      padding: 'var(--space-3) var(--space-4)',
      marginBottom: 'var(--space-4)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      background: v.iconBg,
      color: v.iconColor,
      fontFamily: 'var(--font-pixel)',
      fontSize: '0.6rem',
      width: '1.5rem',
      height: '1.5rem',
      flexShrink: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontWeight: 'bold',
      alignSelf: 'flex-start',
      marginTop: '0.1rem'
    }
  }, "i"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, title && /*#__PURE__*/React.createElement("strong", {
    style: {
      fontFamily: 'var(--font-pixel)',
      fontSize: 'var(--fs-pixel-sm)',
      color: 'var(--text)',
      textTransform: 'uppercase',
      display: 'block',
      marginBottom: 'var(--space-2)'
    }
  }, title), /*#__PURE__*/React.createElement("p", {
    style: {
      fontFamily: 'var(--font-data)',
      fontSize: 'var(--fs-data-sm)',
      color: 'var(--muted)',
      margin: 0,
      lineHeight: 1.6
    }
  }, children), link && /*#__PURE__*/React.createElement("a", {
    href: link,
    style: {
      fontFamily: 'var(--font-pixel)',
      fontSize: 'var(--fs-pixel-xs)',
      color: v.borderColor,
      textDecoration: 'none',
      display: 'block',
      marginTop: 'var(--space-2)'
    }
  }, linkText)));
}
Object.assign(__ds_scope, { HelpBox });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/HelpBox.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Message.jsx
try { (() => {
function Message({
  children,
  variant = 'ok',
  onDismiss
}) {
  const variants = {
    ok: {
      borderColor: 'var(--green)',
      color: 'var(--green)',
      background: 'rgba(0,255,85,0.08)'
    },
    err: {
      borderColor: 'var(--red)',
      color: 'var(--red)',
      background: 'rgba(255,17,68,0.08)'
    },
    info: {
      borderColor: 'var(--accent2)',
      color: 'var(--accent2)',
      background: 'rgba(0,212,255,0.08)'
    },
    warn: {
      borderColor: 'var(--accent)',
      color: 'var(--accent)',
      background: 'rgba(255,230,0,0.08)'
    }
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-pixel)',
      fontSize: 'var(--fs-pixel-sm)',
      textTransform: 'uppercase',
      padding: 'var(--space-2) var(--space-4)',
      border: '2px solid',
      marginBottom: 'var(--space-3)',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      gap: 'var(--space-2)',
      ...(variants[variant] ?? variants.ok)
    }
  }, /*#__PURE__*/React.createElement("span", null, children), onDismiss && /*#__PURE__*/React.createElement("button", {
    onClick: onDismiss,
    style: {
      background: 'none',
      border: 'none',
      cursor: 'pointer',
      color: 'inherit',
      fontFamily: 'var(--font-pixel)',
      fontSize: 'var(--fs-pixel-sm)',
      padding: '0 var(--space-1)',
      boxShadow: 'none',
      lineHeight: 1,
      opacity: 0.7
    }
  }, "\xD7"));
}
Object.assign(__ds_scope, { Message });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Message.jsx", error: String((e && e.message) || e) }); }

// components/feedback/ProgressBar.jsx
try { (() => {
function ProgressBar({
  value = 0,
  max = 100,
  label,
  showPercent = false
}) {
  const pct = Math.min(100, Math.max(0, max > 0 ? value / max * 100 : 0));
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 'var(--space-2)'
    }
  }, (label || showPercent) && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      fontFamily: 'var(--font-data)',
      fontSize: 'var(--fs-data-sm)',
      color: 'var(--muted)'
    }
  }, label && /*#__PURE__*/React.createElement("span", null, label), showPercent && /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--green)'
    }
  }, Math.round(pct), "%")), /*#__PURE__*/React.createElement("div", {
    style: {
      background: '#1a1a40',
      border: '1px solid var(--border)',
      height: '12px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--green)',
      height: '100%',
      width: `${pct}%`,
      transition: 'width 0.3s'
    }
  })));
}
Object.assign(__ds_scope, { ProgressBar });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/ProgressBar.jsx", error: String((e && e.message) || e) }); }

// components/forms/DropZone.jsx
try { (() => {
function DropZone({
  onFile,
  accept,
  label = 'Trascina il file qui',
  sublabel,
  fileName
}) {
  const [dragging, setDragging] = React.useState(false);
  const inputRef = React.useRef(null);
  const handleDrop = e => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (file && onFile) onFile(file);
  };
  const handleInputChange = e => {
    const file = e.target.files && e.target.files[0];
    if (file && onFile) onFile(file);
  };
  const isConfirmed = !!fileName;
  const isActive = dragging || isConfirmed;
  return /*#__PURE__*/React.createElement("div", {
    onClick: () => inputRef.current && inputRef.current.click(),
    onDrop: handleDrop,
    onDragOver: e => {
      e.preventDefault();
      setDragging(true);
    },
    onDragLeave: () => setDragging(false),
    style: {
      border: `2px dashed ${isActive ? 'var(--accent)' : 'var(--border)'}`,
      background: dragging ? 'rgba(255,230,0,0.05)' : 'var(--surface)',
      textAlign: 'center',
      padding: 'var(--space-8) var(--space-4)',
      cursor: 'pointer',
      color: isActive ? 'var(--accent)' : 'var(--muted)',
      userSelect: 'none'
    }
  }, /*#__PURE__*/React.createElement("input", {
    ref: inputRef,
    type: "file",
    accept: accept,
    style: {
      display: 'none'
    },
    onChange: handleInputChange
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-pixel)',
      fontSize: 'var(--fs-pixel-sm)',
      textTransform: 'uppercase',
      marginBottom: sublabel && !isConfirmed ? 'var(--space-2)' : 0
    }
  }, isConfirmed ? `✓ ${fileName}` : label), sublabel && !isConfirmed && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-data)',
      fontSize: 'var(--fs-data-sm)',
      marginTop: 'var(--space-1)',
      color: 'var(--muted)'
    }
  }, sublabel));
}
Object.assign(__ds_scope, { DropZone });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/DropZone.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function Input({
  label,
  id,
  type = 'text',
  placeholder,
  value,
  onChange,
  disabled = false,
  error,
  helpText,
  required = false
}) {
  const [focused, setFocused] = React.useState(false);
  const borderColor = error ? 'var(--red)' : focused ? 'var(--accent)' : 'var(--border)';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 'var(--space-1)',
      width: '100%'
    }
  }, label && /*#__PURE__*/React.createElement("label", {
    htmlFor: id,
    style: {
      fontFamily: 'var(--font-pixel)',
      fontSize: 'var(--fs-pixel-sm)',
      textTransform: 'uppercase',
      letterSpacing: '0.08em',
      color: 'var(--muted)',
      display: 'block'
    }
  }, label, required && /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--red)',
      marginLeft: '0.25rem'
    }
  }, "*")), /*#__PURE__*/React.createElement("input", {
    id: id,
    type: type,
    placeholder: placeholder,
    value: value,
    onChange: onChange,
    disabled: disabled,
    required: required,
    style: {
      background: 'var(--bg)',
      border: `2px solid ${borderColor}`,
      color: 'var(--text)',
      fontFamily: 'var(--font-data)',
      fontSize: 'var(--fs-data-md)',
      padding: 'var(--space-2) var(--space-3)',
      width: '100%',
      outline: 'none',
      opacity: disabled ? 0.5 : 1,
      boxShadow: focused ? `0 0 0 1px ${borderColor}` : 'none'
    },
    onFocus: () => setFocused(true),
    onBlur: () => setFocused(false)
  }), error && /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-pixel)',
      fontSize: 'var(--fs-pixel-xs)',
      color: 'var(--red)',
      textTransform: 'uppercase'
    }
  }, error), helpText && !error && /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-data)',
      fontSize: 'var(--fs-data-sm)',
      color: 'var(--muted)'
    }
  }, helpText));
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/forms/WizardSteps.jsx
try { (() => {
function WizardSteps({
  steps = [],
  current = 1,
  onNavigate
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      marginBottom: 'var(--space-8)',
      borderBottom: '2px solid var(--border)'
    }
  }, steps.map((step, i) => {
    const num = i + 1;
    const isDone = num < current;
    const isActive = num === current;
    return /*#__PURE__*/React.createElement("div", {
      key: num,
      onClick: onNavigate && !isActive ? () => onNavigate(num) : undefined,
      style: {
        flex: 1,
        textAlign: 'center',
        fontFamily: 'var(--font-pixel)',
        fontSize: 'var(--fs-pixel-sm)',
        textTransform: 'uppercase',
        cursor: onNavigate && !isActive ? 'pointer' : 'default',
        padding: 'var(--space-2) var(--space-3)',
        marginBottom: '-2px',
        color: isDone ? 'var(--green)' : isActive ? 'var(--bg)' : 'var(--muted)',
        background: isActive ? 'var(--accent)' : 'transparent',
        borderBottom: isDone ? '3px solid var(--green)' : isActive ? '3px solid var(--accent2)' : '3px solid transparent'
      }
    }, num, " \u2014 ", step);
  }));
}
Object.assign(__ds_scope, { WizardSteps });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/WizardSteps.jsx", error: String((e && e.message) || e) }); }

// components/navigation/Tabs.jsx
try { (() => {
function TabButton({
  tab,
  isActive,
  onClick
}) {
  const [hovered, setHovered] = React.useState(false);
  return /*#__PURE__*/React.createElement("button", {
    onClick: onClick,
    style: {
      fontFamily: 'var(--font-pixel)',
      fontSize: 'var(--fs-pixel-xs)',
      textTransform: 'uppercase',
      letterSpacing: '0.08em',
      padding: 'var(--space-2) var(--space-3)',
      background: isActive ? 'var(--accent)' : 'transparent',
      color: isActive ? 'var(--bg)' : hovered ? 'var(--text)' : 'var(--muted)',
      border: 'none',
      borderBottom: isActive ? '2px solid var(--accent2)' : '2px solid transparent',
      cursor: 'pointer',
      boxShadow: 'none',
      marginBottom: '-2px',
      whiteSpace: 'nowrap'
    },
    onMouseEnter: () => setHovered(true),
    onMouseLeave: () => setHovered(false)
  }, tab.label);
}
function Tabs({
  tabs = [],
  defaultTab,
  children
}) {
  const [active, setActive] = React.useState(defaultTab || tabs[0] && tabs[0].id || '');
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 0,
      borderBottom: '2px solid var(--border)',
      marginBottom: 'var(--space-5)'
    }
  }, tabs.map(tab => /*#__PURE__*/React.createElement(TabButton, {
    key: tab.id,
    tab: tab,
    isActive: tab.id === active,
    onClick: () => setActive(tab.id)
  }))), /*#__PURE__*/React.createElement("div", null, typeof children === 'function' ? children(active) : children));
}
Object.assign(__ds_scope, { Tabs });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/Tabs.jsx", error: String((e && e.message) || e) }); }

// components/overlay/Modal.jsx
try { (() => {
function Modal({
  open,
  title,
  children,
  onClose,
  actions
}) {
  if (!open) return null;
  return /*#__PURE__*/React.createElement("div", {
    onClick: e => {
      if (e.target === e.currentTarget && onClose) onClose();
    },
    style: {
      position: 'fixed',
      inset: 0,
      background: 'rgba(0,0,0,0.75)',
      zIndex: 10000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--surface)',
      border: '2px solid var(--accent)',
      boxShadow: 'var(--shadow-modal)',
      padding: 'var(--space-6)',
      maxWidth: '480px',
      width: '90%'
    }
  }, title && /*#__PURE__*/React.createElement("h3", {
    style: {
      fontFamily: 'var(--font-pixel)',
      fontSize: 'var(--fs-pixel-md)',
      color: 'var(--accent)',
      marginBottom: 'var(--space-3)',
      textTransform: 'uppercase',
      letterSpacing: '0.05em'
    }
  }, title), /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: actions ? 'var(--space-4)' : 0
    }
  }, children), actions && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 'var(--space-2)',
      flexWrap: 'wrap'
    }
  }, actions)));
}
Object.assign(__ds_scope, { Modal });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/overlay/Modal.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Panel = __ds_scope.Panel;

__ds_ns.Table = __ds_scope.Table;

__ds_ns.EmptyState = __ds_scope.EmptyState;

__ds_ns.HelpBox = __ds_scope.HelpBox;

__ds_ns.Message = __ds_scope.Message;

__ds_ns.ProgressBar = __ds_scope.ProgressBar;

__ds_ns.DropZone = __ds_scope.DropZone;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.WizardSteps = __ds_scope.WizardSteps;

__ds_ns.Tabs = __ds_scope.Tabs;

__ds_ns.Modal = __ds_scope.Modal;

})();
