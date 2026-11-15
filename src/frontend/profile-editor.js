"use strict";

// Editing your own profile (load after profile-render.js):
//   new Collectivize.ProfileEditor({ view, renderer, save, onSaved, onCancel }).mount(container)
//
// One form covers everything about your page: your name and text, Top 3,
// website, colors, the layout (which sections show and in what order)
// and who can see what (your profile, the events you're going to, your
// connections). The right-hand
// side is a live preview drawn by the same renderer as the real page.

(() => {
    const { el, ProfileRules, ProfileTheme, SECTION_LABELS, BACKGROUND_PICTURES } = window.Collectivize.Profile;

    const SWATCHES = ["#E8452F", "#19A88A", "#1E3A9E", "#3D6BFF", "#000000", "#FDFDFB", "#F5F4F0", "#202B29"];
    const SECTIONS = Object.keys(SECTION_LABELS);
    const AUDIENCES = [
        ["network", "Everyone signed in"],
        ["connections", "My connections only"],
        ["private", "Only me"],
    ];

    // Edit mode: a form on the left and a live preview (the same renderer)
    // on the right. `save(changes)` sends the edit and resolves with the
    // saved profile; a rejected save shows its message under the buttons.
    class ProfileEditor {
        constructor({ view, renderer, save, onSaved, onCancel }) {
            this.view = view;
            this.renderer = renderer;
            this.send = save;
            this.onSaved = onSaved;
            this.onCancel = onCancel;
            this.fields = {};
            const settings = view.settings || {};
            const shown = (view.sections || SECTIONS).filter((key) => SECTIONS.includes(key));
            const top3 = view.top3 || { title: "", items: ["", "", ""] };
            this.draft = {
                display_name: view.name || "",
                bio: view.bio || "",
                about: view.about || "",
                top3_title: top3.title,
                top3_items: [...top3.items],
                website: view.website || "",
                background: view.colors.background,
                outline: view.colors.outline,
                background_picture: BACKGROUND_PICTURES[view.background_picture] ? view.background_picture : "",
                // Shown sections in their order, then the hidden ones.
                sections: [
                    ...shown.map((key) => ({ key, shown: true })),
                    ...SECTIONS.filter((key) => !shown.includes(key)).map((key) => ({ key, shown: false })),
                ],
                profile_visibility: AUDIENCES.some(([value]) => value === settings.profile_visibility)
                    ? settings.profile_visibility : "network",
                rsvp_visibility: AUDIENCES.some(([value]) => value === settings.rsvp_visibility)
                    ? settings.rsvp_visibility : "connections",
                hide_connections: settings.hide_connections === true,
            };
        }

        mount(container) {
            this.form = el("form", { className: "edit-form", attrs: { novalidate: true, "aria-label": "Edit profile" } });
            this.form.append(
                this.group("Name", [
                    this.textField("display_name", "Display name", { max: ProfileRules.LIMITS.display_name, hint: "The name people see." }),
                ]),
                this.group("About you", [
                    this.textField("bio", "Bio", { max: ProfileRules.LIMITS.bio, hint: "One line." }),
                    this.textField("about", "About", { max: ProfileRules.LIMITS.about, multiline: true }),
                ]),
                this.group("Top 3", [
                    this.textField("top3_title", "Title", { max: ProfileRules.LIMITS.top3_title, placeholder: "Top 3 study spots" }),
                    ...[0, 1, 2].map((i) => this.textField(`top3_${i}`, `Item ${i + 1}`, { max: ProfileRules.LIMITS.top3_item })),
                ], "Optional. Leave all four empty to hide it."),
                this.group("Links", [
                    this.textField("website", "Website", { type: "url", placeholder: "https://", hint: "Optional. Must start with https://", counter: false }),
                ]),
                this.group("Colors", [
                    this.colorField("background", "Background"),
                    this.colorField("outline", "Outline"),
                    this.outlineNote = el("p", { className: "edit-note", attrs: { hidden: true } }),
                ]),
                this.group("Background picture", [this.pictureField()], "A banner across the top of your page."),
                this.group("Layout", [this.layoutList = el("ol", { className: "edit-layout-list" })],
                    "Choose which sections visitors see, and in what order."),
                this.group("Who can see what", [
                    this.choiceField("profile_visibility", "Your profile",
                        "Others still see your name, but not what's on your page."),
                    this.choiceField("rsvp_visibility", "Events you're going to",
                        "Applies to your page, to Discover and to calendars."),
                    this.toggleField("hide_connections", "Hide who I'm connected to",
                        "Visitors won't see your connections on your network bubble or anywhere else."),
                ]),
                this.actions(),
            );
            this.form.addEventListener("submit", (event) => {
                event.preventDefault();
                this.save();
            });

            this.preview = el("div", { className: "edit-preview-body" });
            container.replaceChildren(el("div", { className: "edit-layout" }, [
                this.form,
                el("section", { className: "edit-preview", attrs: { "aria-label": "Live preview" } }, [
                    el("p", { className: "edit-preview-label", text: "Live preview · as visitors see it" }),
                    this.preview,
                ]),
            ]));
            this.refresh();
            this.fields.display_name.input.focus();
        }

        group(title, children, note) {
            return el("fieldset", { className: "edit-group" }, [
                el("legend", { className: "edit-legend", text: title }),
                note ? el("p", { className: "edit-hint", text: note }) : null,
                ...children,
            ]);
        }

        textField(key, label, { max, hint, placeholder, prefix, multiline = false, type = "text", counter = true }) {
            const id = `edit-${key}`;
            const input = el(multiline ? "textarea" : "input", {
                className: "edit-input",
                attrs: {
                    id, name: key, placeholder,
                    type: multiline ? null : type,
                    rows: multiline ? "6" : null,
                    autocomplete: "off",
                    autocapitalize: key === "website" ? "none" : null,
                    spellcheck: key === "website" ? "false" : null,
                    "aria-describedby": `${id}-hint ${id}-error`,
                },
            });
            input.value = this.read(key);
            input.addEventListener("input", () => {
                this.write(key, input.value);
                this.refresh();
            });
            const count = counter && max ? el("span", { className: "edit-count", attrs: { "aria-hidden": "true" } }) : null;
            const error = el("p", { className: "edit-error", attrs: { id: `${id}-error` } });
            this.fields[key] = { input, count, error, max };
            const control = prefix
                ? el("div", { className: "edit-prefixed" }, [el("span", { className: "edit-prefix", text: prefix, attrs: { "aria-hidden": "true" } }), input])
                : input;
            return el("div", { className: "edit-field" }, [
                el("div", { className: "edit-label-row" }, [el("label", { attrs: { for: id }, text: label }), count]),
                control,
                el("p", { className: "edit-hint", text: hint || "", attrs: { id: `${id}-hint` } }),
                error,
            ]);
        }

        colorField(key, label) {
            const swatches = SWATCHES.map((hex) => {
                const button = el("button", {
                    className: "edit-swatch",
                    attrs: { type: "button", "aria-label": `${label} ${hex}`, title: hex },
                });
                button.style.setProperty("--swatch", hex);
                button.addEventListener("click", () => this.setColor(key, hex));
                return button;
            });
            const picker = el("input", {
                className: "edit-picker",
                attrs: { type: "color", id: `edit-${key}`, "aria-label": `Custom ${label.toLowerCase()} color` },
            });
            picker.addEventListener("input", () => this.setColor(key, picker.value));
            const value = el("span", { className: "edit-hex" });
            const error = el("p", { className: "edit-error" });
            this.fields[key] = { swatches, picker, value, error };
            return el("div", { className: "edit-field" }, [
                el("div", { className: "edit-label-row" }, [el("span", { className: "edit-label", text: label }), value]),
                el("div", { className: "edit-swatches", attrs: { role: "group", "aria-label": `${label} color` } }, [
                    ...swatches,
                    el("label", { className: "edit-custom", attrs: { title: "Custom color" } }, [picker, el("span", { text: "Custom" })]),
                ]),
                error,
            ]);
        }

        /** "None" plus one tile per preset picture (kept out of this.fields: no text, no errors). */
        pictureField() {
            const choices = [["", "None"], ...Object.entries(BACKGROUND_PICTURES)];
            this.pictureButtons = choices.map(([key, name]) => {
                const button = el("button", {
                    className: `edit-picture${key ? ` p-cover-${key}` : " is-none"}`,
                    attrs: { type: "button", title: name, "aria-label": `Background picture: ${name}` },
                });
                if (!key) button.textContent = "None";
                button.dataset.picture = key;
                button.addEventListener("click", () => {
                    this.draft.background_picture = key;
                    this.refresh();
                });
                return button;
            });
            return el("div", { className: "edit-pictures", attrs: { role: "group", "aria-label": "Background picture" } }, this.pictureButtons);
        }

        // --- layout: show, hide and reorder sections -------------------------------

        drawLayout() {
            const { sections } = this.draft;
            this.layoutList.replaceChildren(...sections.map((section, index) => {
                const label = SECTION_LABELS[section.key];
                const id = `edit-section-${section.key}`;
                const box = el("input", { attrs: { type: "checkbox", id } });
                box.checked = section.shown;
                box.addEventListener("change", () => this.editSections((list) => list.map((item) => (
                    item.key === section.key ? { ...item, shown: box.checked } : item))));
                const mover = (text, step, name) => {
                    const button = el("button", {
                        className: "edit-move", text,
                        attrs: { type: "button", "aria-label": `Move ${label} ${name}`, "data-move": `${section.key}:${step}` },
                    });
                    button.disabled = index + step < 0 || index + step >= sections.length;
                    button.addEventListener("click", () => this.moveSection(section.key, step));
                    return button;
                };
                return el("li", { className: section.shown ? "edit-layout-item" : "edit-layout-item is-hidden" }, [
                    box,
                    el("label", { text: label, attrs: { for: id } }),
                    el("span", { className: "edit-layout-state", text: section.shown ? "" : "Hidden" }),
                    mover("↑", -1, "up"),
                    mover("↓", 1, "down"),
                ]);
            }));
        }

        editSections(change) {
            this.draft.sections = change(this.draft.sections);
            this.refresh();
        }

        moveSection(key, step) {
            this.editSections((list) => {
                const from = list.findIndex((item) => item.key === key);
                const to = from + step;
                if (to < 0 || to >= list.length) return list;
                const moved = [...list];
                [moved[from], moved[to]] = [moved[to], moved[from]];
                return moved;
            });
            // Keep the keyboard on the button that was pressed.
            this.layoutList.querySelector(`[data-move="${key}:${step}"]:not(:disabled)`)?.focus();
        }

        // --- who can see what ------------------------------------------------------

        choiceField(key, label, hint) {
            const id = `edit-${key}`;
            const select = el("select", { className: "edit-input", attrs: { id, "aria-describedby": `${id}-hint` } },
                AUDIENCES.map(([value, text]) => el("option", { text, attrs: { value } })));
            select.value = this.draft[key];
            select.addEventListener("change", () => {
                this.draft[key] = select.value;
                this.refresh();
            });
            return el("div", { className: "edit-field" }, [
                el("div", { className: "edit-label-row" }, [el("label", { attrs: { for: id }, text: label })]),
                select,
                el("p", { className: "edit-hint", text: hint, attrs: { id: `${id}-hint` } }),
            ]);
        }

        toggleField(key, label, hint) {
            const id = `edit-${key}`;
            const box = el("input", { attrs: { type: "checkbox", id, "aria-describedby": `${id}-hint` } });
            box.checked = this.draft[key];
            box.addEventListener("change", () => {
                this.draft[key] = box.checked;
                this.refresh();
            });
            return el("div", { className: "edit-field" }, [
                el("div", { className: "edit-check" }, [box, el("label", { attrs: { for: id }, text: label })]),
                el("p", { className: "edit-hint", text: hint, attrs: { id: `${id}-hint` } }),
            ]);
        }

        setColor(key, hex) {
            this.draft[key] = hex.toUpperCase();
            this.refresh();
        }

        actions() {
            this.status = el("p", { className: "edit-status", attrs: { role: "status" } });
            this.saveButton = el("button", { className: "page-button page-button-solid", text: "Save", attrs: { type: "submit" } });
            const cancel = el("button", { className: "page-button", text: "Cancel", attrs: { type: "button" } });
            cancel.addEventListener("click", () => this.onCancel());
            return el("div", { className: "edit-actions" }, [this.saveButton, cancel, this.status]);
        }

        read(key) {
            const match = key.match(/^top3_(\d)$/);
            return match ? this.draft.top3_items[Number(match[1])] : this.draft[key];
        }

        write(key, value) {
            const match = key.match(/^top3_(\d)$/);
            if (match) this.draft.top3_items[Number(match[1])] = value;
            else this.draft[key] = value;
        }

        // Update counters, inline errors, color controls and the preview.
        refresh() {
            const errors = ProfileRules.validate(this.draft);
            this.drawLayout();
            for (const [key, field] of Object.entries(this.fields)) {
                const message = errors[key] || "";
                field.error.textContent = message;
                if (field.input) {
                    field.input.setAttribute("aria-invalid", String(Boolean(message)));
                    if (field.count) {
                        const used = ProfileRules.length(this.read(key));
                        field.count.textContent = `${used}/${field.max}`;
                        field.count.classList.toggle("is-over", used > field.max);
                    }
                } else {
                    const current = this.draft[key];
                    field.value.textContent = current;
                    field.picker.value = current.toLowerCase();
                    for (const swatch of field.swatches) {
                        swatch.setAttribute("aria-pressed", String(swatch.title === current));
                    }
                }
            }
            for (const button of this.pictureButtons) {
                button.setAttribute("aria-pressed", String(button.dataset.picture === this.draft.background_picture));
            }
            const colors = { background: this.draft.background, outline: this.draft.outline };
            const faint = !errors.background && !errors.outline && ProfileTheme.outlineIsFaint(colors);
            this.outlineNote.hidden = !faint;
            this.outlineNote.textContent = faint ? "The outline is hard to see on this background." : "";
            this.saveButton.disabled = Object.keys(errors).length > 0;
            this.status.textContent = "";
            this.renderPreview(errors);
        }

        renderPreview(errors) {
            const changes = ProfileRules.toChanges(this.draft);
            const valid = (key) => !errors[key];
            const view = {
                ...this.view,
                access: "full",
                connection: "none",
                in_common: null,
                name: changes.display_name || this.view.name,
                sections: changes.sections,
                bio: changes.bio,
                about: changes.about,
                top3: changes.top3 && [0, 1, 2].every((i) => valid(`top3_${i}`)) && valid("top3_title") ? changes.top3 : null,
                website: valid("website") ? changes.website : null,
                colors: changes.colors,
                background_picture: changes.background_picture,
            };
            this.preview.replaceChildren(this.renderer.render(view, "preview"));
        }

        async save() {
            const errors = ProfileRules.validate(this.draft);
            if (Object.keys(errors).length) return;
            this.saveButton.disabled = true;
            this.status.textContent = "Saving…";
            try {
                this.onSaved(await this.send(ProfileRules.toChanges(this.draft)));
            } catch (error) {
                this.status.textContent = error instanceof Error ? error.message : "That didn't save.";
                this.saveButton.disabled = false;
            }
        }
    }

    window.Collectivize = Object.freeze({ ...window.Collectivize, ProfileEditor });
})();
