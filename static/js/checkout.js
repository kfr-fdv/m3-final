// Nova Poshta city and branch pickers (checkout and account pages).
// The visible inputs hold names; the hidden inputs get the refs of the picked items.
document.addEventListener('DOMContentLoaded', function () {
    var form = document.querySelector('form[data-cities-url]');
    if (!form) {
        return;
    }

    var SEARCH_DELAY_MS = 300;

    // Run fn only after the user stopped typing for `ms` milliseconds.
    function debounce(fn, ms) {
        var timer;
        return function () {
            var args = arguments;
            clearTimeout(timer);
            timer = setTimeout(function () { fn.apply(null, args); }, ms);
        };
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // "Київ" + "ки" -> "<mark>Ки</mark>їв"
    function highlight(text, query) {
        var safe = escapeHtml(text);
        if (!query) {
            return safe;
        }
        var pattern = new RegExp('(' + query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'ig');
        return safe.replace(pattern, '<mark>$1</mark>');
    }

    function fetchResults(url, signal) {
        return fetch(url, { signal: signal }).then(function (response) {
            if (!response.ok) {
                throw new Error('HTTP ' + response.status);
            }
            return response.json();
        }).then(function (data) {
            return data.results || [];
        });
    }

    /**
     * A search-as-you-type select on top of a text input.
     * options: root, hidden, minChars, hint, empty, load(query, signal), describe(item), onSelect, onClear
     */
    function createSelect(options) {
        var root = options.root;
        var input = root.querySelector('.np-select__input');
        var menu = root.querySelector('.np-select__menu');
        var icon = root.querySelector('.np-select__icon i');
        var items = [];
        var active = -1;
        var request = null;  // AbortController of the request in flight

        function setIcon(state) {
            icon.className = {
                loading: 'fa-solid fa-spinner fa-spin',
                selected: 'fa-solid fa-check',
                idle: 'fa-solid fa-chevron-down'
            }[state];
        }

        function open() {
            menu.hidden = false;
            root.classList.add('is-open');
            input.setAttribute('aria-expanded', 'true');
        }

        function close() {
            menu.hidden = true;
            root.classList.remove('is-open');
            input.setAttribute('aria-expanded', 'false');
            active = -1;
        }

        function showMessage(text, iconClass) {
            menu.innerHTML = '<li class="np-select__message">'
                + (iconClass ? '<i class="' + iconClass + '"></i>' : '')
                + escapeHtml(text) + '</li>';
            open();
        }

        function setActive(index) {
            var options = menu.querySelectorAll('.np-select__option');
            active = index;
            options.forEach(function (option, i) {
                option.classList.toggle('is-active', i === index);
                option.setAttribute('aria-selected', i === index ? 'true' : 'false');
            });
            if (options[index]) {
                options[index].scrollIntoView({ block: 'nearest' });
            }
        }

        function render(query) {
            if (!items.length) {
                showMessage(options.empty, 'fa-regular fa-face-frown');
                return;
            }
            menu.innerHTML = '';
            items.forEach(function (item, index) {
                var view = options.describe(item);
                var li = document.createElement('li');
                li.className = 'np-select__option';
                li.setAttribute('role', 'option');
                li.innerHTML = '<span class="np-select__option-icon"><i class="' + view.icon + '"></i></span>'
                    + '<span class="np-select__option-text">'
                    + '<span class="np-select__title">' + highlight(view.title, query) + '</span>'
                    + (view.subtitle ? '<span class="np-select__subtitle">' + highlight(view.subtitle, query) + '</span>' : '')
                    + '</span>';
                // mousedown instead of click: fires before the input loses focus
                li.addEventListener('mousedown', function (event) {
                    event.preventDefault();
                    choose(index);
                });
                li.addEventListener('mousemove', function () {
                    if (active !== index) {
                        setActive(index);
                    }
                });
                menu.appendChild(li);
            });
            active = -1;
            open();
        }

        function select(item) {
            input.value = options.describe(item).label;
            options.hidden.value = item.ref;
            root.classList.add('is-selected');
            setIcon('selected');
        }

        function choose(index, byUser) {
            select(items[index]);
            close();
            if (options.onSelect) {
                options.onSelect(items[index], byUser !== false);
            }
        }

        function clearSelection() {
            if (!options.hidden.value) {
                return;
            }
            options.hidden.value = '';
            root.classList.remove('is-selected');
            if (options.onClear) {
                options.onClear();
            }
        }

        function search() {
            var query = input.value.trim();
            if (request) {
                request.abort();  // an older, slower answer must not overwrite a newer one
            }
            if (query.length < options.minChars) {
                items = [];
                setIcon('idle');
                showMessage(options.hint);
                return Promise.resolve([]);
            }
            request = new AbortController();
            setIcon('loading');
            return options.load(query, request.signal).then(function (result) {
                items = result;
                setIcon(options.hidden.value ? 'selected' : 'idle');
                if (document.activeElement === input) {
                    render(query);
                }
                return result;
            }).catch(function (error) {
                if (error.name === 'AbortError') {
                    return [];
                }
                setIcon('idle');
                showMessage('Сервіс доставки недоступний. Спробуйте пізніше.', 'fa-solid fa-triangle-exclamation');
                return [];
            });
        }

        var searchLater = debounce(search, SEARCH_DELAY_MS);

        input.addEventListener('input', function () {
            clearSelection();
            setIcon('idle');
            searchLater();
        });

        // Open the list on focus, and on a click when the input already has focus.
        function openList() {
            if (!input.disabled && !options.hidden.value && menu.hidden) {
                search();
            }
        }
        input.addEventListener('focus', openList);
        input.addEventListener('click', openList);

        input.addEventListener('blur', close);

        input.addEventListener('keydown', function (event) {
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                if (menu.hidden) {
                    search();
                } else if (items.length) {
                    setActive(Math.min(active + 1, items.length - 1));
                }
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                setActive(Math.max(active - 1, 0));
            } else if (event.key === 'Enter' && !menu.hidden) {
                // Enter in an open list never submits the form: it picks the highlighted
                // item, or the first one when nothing is highlighted yet.
                event.preventDefault();
                if (items.length) {
                    choose(Math.max(active, 0));
                }
            } else if (event.key === 'Escape') {
                close();
            }
        });

        if (options.hidden.value) {
            root.classList.add('is-selected');
            setIcon('selected');
        }

        return {
            input: input,
            search: search,
            reset: function () {
                if (request) {
                    request.abort();
                }
                input.value = '';
                options.hidden.value = '';
                items = [];
                root.classList.remove('is-selected');
                setIcon('idle');
                close();
            },
            setDisabled: function (disabled) {
                input.disabled = disabled;
                root.classList.toggle('is-disabled', disabled);
            },
            // The city from the profile matches one city exactly: pick it without opening the menu.
            pickExact: function () {
                var name = input.value.trim().toLowerCase();
                if (name.length < options.minChars) {
                    return;
                }
                options.load(name, undefined).then(function (result) {
                    var exact = result.filter(function (item) { return item.name.toLowerCase() === name; });
                    if (exact.length === 1 && !options.hidden.value) {
                        items = exact;
                        choose(0, false);
                    }
                }).catch(function () {});
            }
        };
    }

    var cityRef = form.querySelector('[name="city_ref"]');
    var branchRef = form.querySelector('[name="warehouse_ref"]');
    var branchLabel = form.querySelector('label[for="warehouse"]');
    var branchIcon = document.getElementById('warehouse-icon');
    var payButton = document.querySelector('.order-card__pay');

    function deliveryType() {
        var checked = form.querySelector('[name="delivery_type"]:checked');
        return checked ? checked.value : 'branch';
    }

    function isPostomat() {
        return deliveryType() === 'postomat';
    }

    var branch = createSelect({
        root: document.getElementById('warehouse-select'),
        hidden: branchRef,
        minChars: 0,
        hint: 'Спершу оберіть місто.',
        empty: 'Нічого не знайдено. Спробуйте номер або вулицю.',
        load: function (query, signal) {
            return fetchResults(form.dataset.warehousesUrl
                + '?city=' + encodeURIComponent(cityRef.value)
                + '&type=' + deliveryType()
                + '&q=' + encodeURIComponent(query), signal);
        },
        describe: function (item) {
            // "Відділення №1: вул. Хрещатик, 1" -> title "Відділення №1", subtitle the address
            var parts = item.name.split(/:\s(.+)/);
            return {
                label: item.name,
                title: parts[0],
                subtitle: parts[1] || '',
                icon: item.is_postomat ? 'fa-solid fa-box' : 'fa-solid fa-building'
            };
        },
        onSelect: updateSteps,
        onClear: updateSteps
    });

    function updateBranchField() {
        var noCity = !cityRef.value;
        branchLabel.textContent = isPostomat() ? 'Поштомат' : 'Відділення';
        if (branchIcon) {
            branchIcon.className = (isPostomat() ? 'fa-solid fa-box' : 'fa-solid fa-building') + ' field-box__icon';
        }
        branch.input.placeholder = noCity
            ? 'Спершу оберіть місто'
            : (isPostomat() ? 'Номер поштомата або вулиця' : 'Номер відділення або вулиця');
        branch.setDisabled(noCity);
        updateSteps();
    }

    // Steps above the form: a step is done when all its required fields are filled.
    function updateSteps() {
        var firstOpen = null;
        form.querySelectorAll('.checkout-step').forEach(function (step) {
            var fields = form.querySelectorAll('[data-step-field="' + step.dataset.step + '"]');
            var done = Array.prototype.every.call(fields, function (field) {
                if (field.type === 'radio') {
                    return form.querySelector('[name="' + field.name + '"]:checked') !== null;
                }
                return field.value.trim() !== '';
            });
            step.classList.toggle('is-done', done);
            if (!done && firstOpen === null) {
                firstOpen = step;
            }
        });
        form.querySelectorAll('.checkout-step').forEach(function (step) {
            step.classList.toggle('is-current', step === (firstOpen || step.parentNode.lastElementChild));
        });
    }

    // Cash on delivery: nothing is paid now, so the button only confirms the order.
    function updatePayButton() {
        if (!payButton) {
            return;
        }
        var cash = form.querySelector('[name="payment_method"]:checked');
        payButton.textContent = cash && cash.value === 'cod'
            ? 'Підтвердити замовлення'
            : 'Оплатити ' + payButton.dataset.total;
    }

    var city = createSelect({
        root: document.getElementById('city-select'),
        hidden: cityRef,
        minChars: 2,
        hint: 'Введіть щонайменше 2 літери.',
        empty: 'Такого міста не знайдено. Перевірте назву.',
        load: function (query, signal) {
            return fetchResults(form.dataset.citiesUrl + '?q=' + encodeURIComponent(query), signal);
        },
        describe: function (item) {
            return {
                label: item.label,
                title: item.name,
                subtitle: item.area ? item.area + ' область' : '',
                icon: 'fa-solid fa-location-dot'
            };
        },
        onSelect: function (item, byUser) {
            branch.reset();
            updateBranchField();
            if (byUser) {
                branch.input.focus();  // the next step is the branch
            }
        },
        onClear: function () {
            branch.reset();
            updateBranchField();
        }
    });

    form.querySelectorAll('[name="delivery_type"]').forEach(function (radio) {
        radio.addEventListener('change', function () {
            branch.reset();
            updateBranchField();
        });
    });

    form.addEventListener('input', updateSteps);
    form.addEventListener('change', function () {
        updateSteps();
        updatePayButton();
    });

    updateBranchField();
    updatePayButton();
    if (!cityRef.value && city.input.value.trim()) {
        city.pickExact();
    }
});
