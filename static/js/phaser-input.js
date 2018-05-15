/*!
 * phaser-input - version 2.0.5 
 * Adds input boxes to Phaser like CanvasInput, but also works for WebGL and Mobile, made for Phaser only.
 *
 * OrangeGames
 * Build at 02-06-2017
 * Released under MIT License 
 */

var __extends = (this && this.__extends) || (function () {
    var extendStatics = Object.setPrototypeOf ||
        ({ __proto__: [] } instanceof Array && function (d, b) { d.__proto__ = b; }) ||
        function (d, b) { for (var p in b) if (b.hasOwnProperty(p)) d[p] = b[p]; };
    return function (d, b) {
        extendStatics(d, b);
        function __() { this.constructor = d; }
        d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
    };
})();
var PhaserInput;
(function (PhaserInput) {
    var InputType;
    (function (InputType) {
        InputType[InputType["text"] = 0] = "text";
        InputType[InputType["password"] = 1] = "password";
        InputType[InputType["number"] = 2] = "number";
    })(InputType = PhaserInput.InputType || (PhaserInput.InputType = {}));
    var InputElement = (function () {
        function InputElement(game, id, type, value, focusIn, focusOut) {
            if (type === void 0) { type = InputType.text; }
            if (value === void 0) { value = ''; }
            var _this = this;
            this.id = id;
            this.type = type;
            this.game = game;
            this.focusIn = focusIn;
            this.focusOut = focusOut;
            var canvasTopX = this.game.canvas.getBoundingClientRect().top + document.body.scrollTop;
            this.element = document.createElement('input');
            this.element.id = id;
            this.element.style.position = 'absolute';
            this.element.style.top = canvasTopX + 'px';
            this.element.style.left = (-40).toString() + 'px';
            this.element.style.width = (10).toString() + 'px';
            this.element.style.height = (10).toString() + 'px';
            this.element.style.border = '0px';
            this.element.value = this.value;
            this.element.type = InputType[type];
            this.element.addEventListener('focusin', function () {
                if (_this.focusIn instanceof Phaser.Signal) {
                    _this.focusIn.dispatch();
                }
            });
            this.element.addEventListener('focusout', function () {
                if (_this.focusOut instanceof Phaser.Signal) {
                    _this.focusOut.dispatch();
                }
            });
            document.body.appendChild(this.element);
        }
        InputElement.prototype.addKeyUpListener = function (callback) {
            this.keyUpCallback = callback;
            document.addEventListener('keyup', this.keyUpCallback);
            this.element.addEventListener('input', this.keyUpCallback);
        };
        InputElement.prototype.blockKeyDownEvents = function () {
            document.addEventListener('keydown', this.preventKeyPropagation);
        };
        InputElement.prototype.preventKeyPropagation = function (evt) {
            if (evt.stopPropagation) {
                evt.stopPropagation();
            }
            else {
                event.cancelBubble = true;
            }
        };
        InputElement.prototype.unblockKeyDownEvents = function () {
            document.removeEventListener('keydown', this.preventKeyPropagation);
        };
        InputElement.prototype.removeEventListener = function () {
            document.removeEventListener('keyup', this.keyUpCallback);
            this.element.removeEventListener('input', this.keyUpCallback);
        };
        InputElement.prototype.destroy = function () {
            document.body.removeChild(this.element);
        };
        InputElement.prototype.setMax = function (max, min) {
            if (max === undefined) {
                return;
            }
            if (this.type === InputType.text || this.type === InputType.password) {
                this.element.maxLength = parseInt(max, 10);
            }
            else if (this.type === InputType.number) {
                this.element.max = max;
                if (min === undefined) {
                    return;
                }
                this.element.min = min;
            }
        };
        Object.defineProperty(InputElement.prototype, "value", {
            get: function () {
                return this.element.value;
            },
            set: function (value) {
                this.element.value = value;
            },
            enumerable: true,
            configurable: true
        });
        InputElement.prototype.focus = function () {
            var _this = this;
            this.element.focus();
            if (!this.game.device.desktop && this.game.device.chrome) {
                var originalWidth_1 = window.innerWidth, originalHeight_1 = window.innerHeight;
                var kbAppeared_1 = false;
                var interval_1 = setInterval(function () {
                    if (originalWidth_1 > window.innerWidth || originalHeight_1 > window.innerHeight) {
                        kbAppeared_1 = true;
                    }
                    if (kbAppeared_1 && originalWidth_1 === window.innerWidth && originalHeight_1 === window.innerHeight) {
                        if (_this.focusOut instanceof Phaser.Signal) {
                            _this.focusOut.dispatch();
                        }
                        clearInterval(interval_1);
                    }
                }, 50);
            }
        };
        InputElement.prototype.blur = function () {
            this.element.blur();
        };
        Object.defineProperty(InputElement.prototype, "hasSelection", {
            get: function () {
                if (this.type === InputType.number) {
                    return false;
                }
                return this.element.selectionStart !== this.element.selectionEnd;
            },
            enumerable: true,
            configurable: true
        });
        Object.defineProperty(InputElement.prototype, "caretStart", {
            get: function () {
                return this.element.selectionEnd;
            },
            enumerable: true,
            configurable: true
        });
        Object.defineProperty(InputElement.prototype, "caretEnd", {
            get: function () {
                return this.element.selectionStart;
            },
            enumerable: true,
            configurable: true
        });
        InputElement.prototype.getCaretPosition = function () {
            if (this.type === InputType.number) {
                return -1;
            }
            return this.element.selectionStart;
        };
        InputElement.prototype.setCaretPosition = function (pos) {
            if (this.type === InputType.number) {
                return;
            }
            this.element.setSelectionRange(pos, pos);
        };
        return InputElement;
    }());
    PhaserInput.InputElement = InputElement;
})(PhaserInput || (PhaserInput = {}));
var PhaserInput;
(function (PhaserInput) {
    var ForceCase;
    (function (ForceCase) {
        ForceCase[ForceCase["none"] = 0] = "none";
        ForceCase[ForceCase["lower"] = 1] = "lower";
        ForceCase[ForceCase["upper"] = 2] = "upper";
    })(ForceCase = PhaserInput.ForceCase || (PhaserInput.ForceCase = {}));
    var InputField = (function (_super) {
        __extends(InputField, _super);
        function InputField(game, x, y, inputOptions) {
            if (inputOptions === void 0) { inputOptions = {}; }
            var _this = _super.call(this, game, x, y) || this;
            _this.focusOutOnEnter = true;
            _this.placeHolder = null;
            _this.box = null;
            _this.focus = false;
            _this.value = '';
            _this.windowScale = 1;
            _this.blockInput = true;
            _this.focusIn = new Phaser.Signal();
            _this.focusOut = new Phaser.Signal();
            _this.blink = true;
            _this.cnt = 0;
            _this.inputOptions = inputOptions;
            _this.inputOptions.width = (typeof inputOptions.width === 'number') ? inputOptions.width : 150;
            _this.inputOptions.padding = (typeof inputOptions.padding === 'number') ? inputOptions.padding : 0;
            _this.inputOptions.textAlign = inputOptions.textAlign || 'left';
            _this.inputOptions.type = inputOptions.type || PhaserInput.InputType.text;
            _this.inputOptions.forceCase = (inputOptions.forceCase) ? inputOptions.forceCase : ForceCase.none;
            _this.inputOptions.borderRadius = (typeof inputOptions.borderRadius === 'number') ? inputOptions.borderRadius : 0;
            _this.inputOptions.height = (typeof inputOptions.height === 'number') ? inputOptions.height : 14;
            _this.inputOptions.fillAlpha = (inputOptions.fillAlpha === undefined) ? 1 : inputOptions.fillAlpha;
            _this.inputOptions.selectionColor = inputOptions.selectionColor || 'rgba(179, 212, 253, 0.8)';
            _this.inputOptions.zoom = (!game.device.desktop) ? inputOptions.zoom || false : false;
            _this.box = new PhaserInput.InputBox(_this.game, inputOptions);
            _this.setTexture(_this.box.generateTexture());
            _this.textMask = new PhaserInput.TextMask(_this.game, inputOptions);
            _this.addChild(_this.textMask);
            _this.domElement = new PhaserInput.InputElement(_this.game, 'phaser-input-' + (Math.random() * 10000 | 0).toString(), _this.inputOptions.type, _this.value, _this.focusIn, _this.focusOut);
            _this.domElement.setMax(_this.inputOptions.max, _this.inputOptions.min);
            _this.selection = new PhaserInput.SelectionHighlight(_this.game, _this.inputOptions);
            _this.selection.mask = _this.textMask;
            _this.addChild(_this.selection);
            if (inputOptions.placeHolder && inputOptions.placeHolder.length > 0) {
                _this.placeHolder = new Phaser.Text(game, _this.inputOptions.padding, _this.inputOptions.padding, inputOptions.placeHolder, {
                    font: inputOptions.font || '14px Arial',
                    fontWeight: inputOptions.fontWeight || 'normal',
                    fill: inputOptions.placeHolderColor || '#bfbebd'
                });
                _this.placeHolder.mask = _this.textMask;
                _this.addChild(_this.placeHolder);
            }
            _this.cursor = new Phaser.Text(game, _this.inputOptions.padding, _this.inputOptions.padding - 2, '|', {
                font: inputOptions.font || '14px Arial',
                fontWeight: inputOptions.fontWeight || 'normal',
                fill: inputOptions.cursorColor || '#000000'
            });
            _this.cursor.visible = false;
            _this.addChild(_this.cursor);
            _this.text = new Phaser.Text(game, _this.inputOptions.padding, _this.inputOptions.padding, '', {
                font: inputOptions.font || '14px Arial',
                fontWeight: inputOptions.fontWeight || 'normal',
                fill: inputOptions.fill || '#000000'
            });
            _this.text.mask = _this.textMask;
            _this.addChild(_this.text);
            _this.offscreenText = new Phaser.Text(game, _this.inputOptions.padding, _this.inputOptions.padding, '', {
                font: inputOptions.font || '14px Arial',
                fontWeight: inputOptions.fontWeight || 'normal',
                fill: inputOptions.fill || '#000000'
            });
            _this.updateTextAlignment();
            _this.inputEnabled = true;
            _this.input.useHandCursor = true;
            _this.game.input.onDown.add(_this.checkDown, _this);
            _this.focusOut.add(function () {
                if (PhaserInput.KeyboardOpen) {
                    _this.endFocus();
                    if (_this.inputOptions.zoom) {
                        _this.zoomOut();
                    }
                }
            });
            return _this;
        }
        Object.defineProperty(InputField.prototype, "width", {
            get: function () {
                return this.inputOptions.width;
            },
            set: function (width) {
                this.inputOptions.width = width;
                this.box.resize(width);
                this.textMask.resize(width);
                this.updateTextAlignment();
            },
            enumerable: true,
            configurable: true
        });
        InputField.prototype.updateTextAlignment = function () {
            switch (this.inputOptions.textAlign) {
                case 'left':
                    this.text.anchor.set(0, 0);
                    this.text.x = this.inputOptions.padding;
                    if (null !== this.placeHolder) {
                        this.placeHolder.anchor.set(0, 0);
                    }
                    this.cursor.x = this.inputOptions.padding + this.getCaretPosition();
                    break;
                case 'center':
                    this.text.anchor.set(0.5, 0);
                    this.text.x = this.inputOptions.padding + this.inputOptions.width / 2;
                    if (null !== this.placeHolder) {
                        this.placeHolder.anchor.set(0.5, 0);
                        this.placeHolder.x = this.inputOptions.padding + this.inputOptions.width / 2;
                    }
                    this.cursor.x = this.inputOptions.padding + this.inputOptions.width / 2 - this.text.width / 2 + this.getCaretPosition();
                    break;
                case 'right':
                    this.text.anchor.set(1, 0);
                    this.text.x = this.inputOptions.padding + this.inputOptions.width;
                    if (null !== this.placeHolder) {
                        this.placeHolder.anchor.set(1, 0);
                        this.placeHolder.x = this.inputOptions.padding + this.inputOptions.width;
                    }
                    this.cursor.x = this.inputOptions.padding + this.inputOptions.width;
                    break;
            }
        };
        InputField.prototype.checkDown = function (e) {
            if (!this.value) {
                this.resetText();
            }
            if (this.input.checkPointerOver(e)) {
                if (this.focus) {
                    this.setCaretOnclick(e);
                    return;
                }
                if (this.inputOptions.zoom && !PhaserInput.Zoomed) {
                    this.zoomIn();
                }
                this.startFocus();
            }
            else {
                if (this.focus === true) {
                    this.endFocus();
                    if (this.inputOptions.zoom) {
                        this.zoomOut();
                    }
                }
            }
        };
        InputField.prototype.update = function () {
            this.text.update();
            if (this.placeHolder) {
                this.placeHolder.update();
            }
            if (!this.focus) {
                return;
            }
            if (this.cnt !== 30) {
                return this.cnt++;
            }
            this.cursor.visible = this.blink;
            this.blink = !this.blink;
            this.cnt = 0;
        };
        InputField.prototype.endFocus = function () {
            var _this = this;
            if (!this.focus) {
                return;
            }
            this.domElement.removeEventListener();
            if (this.blockInput === true) {
                this.domElement.unblockKeyDownEvents();
            }
            this.focus = false;
            if (this.value.length === 0 && null !== this.placeHolder) {
                this.placeHolder.visible = true;
            }
            this.cursor.visible = false;
            if (this.game.device.desktop) {
                setTimeout(function () {
                    _this.domElement.blur();
                }, 0);
            }
            else {
                this.domElement.blur();
            }
            if (!this.game.device.desktop) {
                PhaserInput.KeyboardOpen = false;
                PhaserInput.onKeyboardClose.dispatch();
            }
        };
        InputField.prototype.startFocus = function () {
            var _this = this;
            this.focus = true;
            if (null !== this.placeHolder) {
                this.placeHolder.visible = false;
            }
            if (this.game.device.desktop) {
                setTimeout(function () {
                    _this.keyUpProcessor();
                }, 0);
            }
            else {
                this.keyUpProcessor();
            }
            if (!this.game.device.desktop) {
                PhaserInput.KeyboardOpen = true;
                PhaserInput.onKeyboardOpen.dispatch();
            }
        };
        InputField.prototype.keyUpProcessor = function () {
            this.domElement.addKeyUpListener(this.keyListener.bind(this));
            this.domElement.focus();
            if (this.blockInput === true) {
                this.domElement.blockKeyDownEvents();
            }
        };
        InputField.prototype.updateText = function () {
            var text = '';
            if (this.inputOptions.type === PhaserInput.InputType.password) {
                for (var i = 0; i < this.value.length; i++) {
                    text += '*';
                }
            }
            else if (this.inputOptions.type === PhaserInput.InputType.number) {
                var val = parseInt(this.value);
                if (val < parseInt(this.inputOptions.min)) {
                    text = this.value = this.domElement.value = this.inputOptions.min;
                }
                else if (val > parseInt(this.inputOptions.max)) {
                    text = this.value = this.domElement.value = this.inputOptions.max;
                }
                else {
                    text = this.value;
                }
            }
            else {
                text = this.value;
            }
            this.text.setText(text);
            if (this.text.width > this.inputOptions.width) {
                this.text.anchor.x = 1;
                this.text.x = this.inputOptions.padding + this.inputOptions.width;
            }
            else {
                switch (this.inputOptions.textAlign) {
                    case 'left':
                        this.text.anchor.set(0, 0);
                        this.text.x = this.inputOptions.padding;
                        break;
                    case 'center':
                        this.text.anchor.set(0.5, 0);
                        this.text.x = this.inputOptions.padding + this.inputOptions.width / 2;
                        break;
                    case 'right':
                        this.text.anchor.set(1, 0);
                        this.text.x = this.inputOptions.padding + this.inputOptions.width;
                        break;
                }
            }
        };
        InputField.prototype.updateCursor = function () {
            if (this.text.width > this.inputOptions.width || this.inputOptions.textAlign === 'right') {
                this.cursor.x = this.inputOptions.padding + this.inputOptions.width;
            }
            else {
                switch (this.inputOptions.textAlign) {
                    case 'left':
                        this.cursor.x = this.inputOptions.padding + this.getCaretPosition();
                        break;
                    case 'center':
                        this.cursor.x = this.inputOptions.padding + this.inputOptions.width / 2 - this.text.width / 2 + this.getCaretPosition();
                        break;
                }
            }
        };
        InputField.prototype.getCaretPosition = function () {
            var caretPosition = this.domElement.getCaretPosition();
            if (-1 === caretPosition) {
                return this.text.width;
            }
            var text = this.value;
            if (this.inputOptions.type === PhaserInput.InputType.password) {
                text = '';
                for (var i = 0; i < this.value.length; i++) {
                    text += '*';
                }
            }
            this.offscreenText.setText(text.slice(0, caretPosition));
            return this.offscreenText.width;
        };
        InputField.prototype.setCaretOnclick = function (e) {
            var localX = (this.text.toLocal(new PIXI.Point(e.x, e.y), this.game.world)).x;
            if (this.inputOptions.textAlign && this.inputOptions.textAlign === 'center') {
                localX += this.text.width / 2;
            }
            var characterWidth = this.text.width / this.value.length;
            var index = 0;
            for (var i = 0; i < this.value.length; i++) {
                if (localX >= i * characterWidth && localX <= (i + 1) * characterWidth) {
                    index = i;
                    break;
                }
            }
            if (localX > (this.value.length - 1) * characterWidth) {
                index = this.value.length;
            }
            this.startFocus();
            this.domElement.setCaretPosition(index);
            this.updateCursor();
        };
        InputField.prototype.updateSelection = function () {
            if (this.domElement.hasSelection) {
                var text = this.value;
                if (this.inputOptions.type === PhaserInput.InputType.password) {
                    text = '';
                    for (var i = 0; i < this.value.length; i++) {
                        text += '*';
                    }
                }
                text = text.substring(this.domElement.caretStart, this.domElement.caretEnd);
                this.offscreenText.setText(text);
                this.selection.updateSelection(this.offscreenText.getBounds());
                switch (this.inputOptions.textAlign) {
                    case 'left':
                        this.selection.x = this.inputOptions.padding;
                        break;
                    case 'center':
                        this.selection.x = this.inputOptions.padding + this.inputOptions.width / 2 - this.text.width / 2;
                        break;
                }
            }
            else {
                this.selection.clear();
            }
        };
        InputField.prototype.zoomIn = function () {
            if (PhaserInput.Zoomed) {
                return;
            }
            var bounds = this.getBounds();
            if (window.innerHeight > window.innerWidth) {
                this.windowScale = this.game.width / (bounds.width * 1.5);
            }
            else {
                this.windowScale = (this.game.width / 2) / (bounds.width * 1.5);
            }
            var offsetX = ((this.game.width - bounds.width * 1.5) / 2) / this.windowScale;
            this.game.world.scale.set(this.game.world.scale.x * this.windowScale, this.game.world.scale.y * this.windowScale);
            this.game.world.pivot.set(bounds.x - offsetX, bounds.y - this.inputOptions.padding * 2);
            PhaserInput.Zoomed = true;
        };
        InputField.prototype.zoomOut = function () {
            if (!PhaserInput.Zoomed) {
                return;
            }
            this.game.world.scale.set(this.game.world.scale.x / this.windowScale, this.game.world.scale.y / this.windowScale);
            this.game.world.pivot.set(0, 0);
            PhaserInput.Zoomed = false;
        };
        InputField.prototype.keyListener = function (evt) {
            this.value = this.getFormattedText(this.domElement.value);
            if (evt.keyCode === 13) {
                if (this.focusOutOnEnter) {
                    this.endFocus();
                }
                return;
            }
            this.updateText();
            this.updateCursor();
            this.updateSelection();
            evt.preventDefault();
        };
        InputField.prototype.destroy = function (destroyChildren) {
            this.game.input.onDown.remove(this.checkDown, this);
            this.focusIn.removeAll();
            this.focusOut.removeAll();
            this.domElement.destroy();
            _super.prototype.destroy.call(this, destroyChildren);
        };
        InputField.prototype.resetText = function () {
            this.setText();
        };
        InputField.prototype.setText = function (text) {
            if (text === void 0) { text = ''; }
            if (null !== this.placeHolder) {
                if (text.length > 0) {
                    this.placeHolder.visible = false;
                }
                else {
                    this.placeHolder.visible = true;
                }
            }
            this.value = this.getFormattedText(text);
            this.domElement.value = this.value;
            this.updateText();
            this.updateCursor();
            this.endFocus();
        };
        InputField.prototype.getFormattedText = function (text) {
            switch (this.inputOptions.forceCase) {
                default:
                case ForceCase.none:
                    return text;
                case ForceCase.lower:
                    return text.toLowerCase();
                case ForceCase.upper:
                    return text.toUpperCase();
            }
        };
        return InputField;
    }(Phaser.Sprite));
    PhaserInput.InputField = InputField;
})(PhaserInput || (PhaserInput = {}));
var PhaserInput;
(function (PhaserInput) {
    var InputBox = (function (_super) {
        __extends(InputBox, _super);
        function InputBox(game, inputOptions) {
            var _this = _super.call(this, game, 0, 0) || this;
            _this.bgColor = (inputOptions.backgroundColor) ? parseInt(inputOptions.backgroundColor.slice(1), 16) : 0xffffff;
            _this.borderRadius = inputOptions.borderRadius || 0;
            _this.borderWidth = inputOptions.borderWidth || 1;
            _this.borderColor = (inputOptions.borderColor) ? parseInt(inputOptions.borderColor.slice(1), 16) : 0x959595;
            _this.boxAlpha = inputOptions.fillAlpha;
            _this.padding = inputOptions.padding;
            var height = inputOptions.height;
            var width = inputOptions.width;
            var height;
            if (inputOptions.font) {
                height = Math.max(parseInt(inputOptions.font.substr(0, inputOptions.font.indexOf('px')), 10), height);
            }
            _this.boxHeight = _this.padding * 2 + height;
            var width = inputOptions.width;
            _this.boxWidth = _this.padding * 2 + width;
            _this.drawBox();
            return _this;
        }
        InputBox.prototype.resize = function (newWidth) {
            this.boxWidth = this.padding * 2 + newWidth;
            this.drawBox();
        };
        InputBox.prototype.drawBox = function () {
            this.clear()
                .beginFill(this.bgColor, this.boxAlpha)
                .lineStyle(this.borderWidth, this.borderColor, this.boxAlpha);
            if (this.borderRadius > 0) {
                this.drawRoundedRect(0, 0, this.boxWidth, this.boxHeight, this.borderRadius);
            }
            else {
                this.drawRect(0, 0, this.boxWidth, this.boxHeight);
            }
        };
        return InputBox;
    }(Phaser.Graphics));
    PhaserInput.InputBox = InputBox;
})(PhaserInput || (PhaserInput = {}));
var PhaserInput;
(function (PhaserInput) {
    var SelectionHighlight = (function (_super) {
        __extends(SelectionHighlight, _super);
        function SelectionHighlight(game, inputOptions) {
            var _this = _super.call(this, game, inputOptions.padding, inputOptions.padding) || this;
            _this.inputOptions = inputOptions;
            return _this;
        }
        SelectionHighlight.prototype.updateSelection = function (rect) {
            var color = Phaser.Color.webToColor(this.inputOptions.selectionColor);
            this.clear();
            this.beginFill(SelectionHighlight.rgb2hex(color), color.a);
            this.drawRect(rect.x, rect.y, rect.width, rect.height - this.inputOptions.padding);
        };
        SelectionHighlight.rgb2hex = function (color) {
            return parseInt(("0" + color.r.toString(16)).slice(-2) +
                ("0" + color.g.toString(16)).slice(-2) +
                ("0" + color.b.toString(16)).slice(-2), 16);
        };
        return SelectionHighlight;
    }(Phaser.Graphics));
    PhaserInput.SelectionHighlight = SelectionHighlight;
})(PhaserInput || (PhaserInput = {}));
var PhaserInput;
(function (PhaserInput) {
    var TextMask = (function (_super) {
        __extends(TextMask, _super);
        function TextMask(game, inputOptions) {
            var _this = _super.call(this, game, inputOptions.padding, inputOptions.padding) || this;
            var height = inputOptions.height;
            if (inputOptions.font) {
                height = Math.max(parseInt(inputOptions.font.substr(0, inputOptions.font.indexOf('px')), 10), height);
            }
            _this.maskWidth = inputOptions.width;
            _this.maskHeight = height * 1.3;
            _this.drawMask();
            return _this;
        }
        TextMask.prototype.resize = function (newWidth) {
            this.maskWidth = newWidth;
            this.drawMask();
        };
        TextMask.prototype.drawMask = function () {
            this.clear()
                .beginFill(0x000000)
                .drawRect(0, 0, this.maskWidth, this.maskHeight)
                .endFill();
        };
        return TextMask;
    }(Phaser.Graphics));
    PhaserInput.TextMask = TextMask;
})(PhaserInput || (PhaserInput = {}));
var PhaserInput;
(function (PhaserInput) {
    PhaserInput.Zoomed = false;
    PhaserInput.KeyboardOpen = false;
    PhaserInput.onKeyboardOpen = new Phaser.Signal();
    PhaserInput.onKeyboardClose = new Phaser.Signal();
    var Plugin = (function (_super) {
        __extends(Plugin, _super);
        function Plugin(game, parent) {
            var _this = _super.call(this, game, parent) || this;
            _this.addInputFieldFactory();
            return _this;
        }
        Plugin.prototype.addInputFieldFactory = function () {
            Phaser.GameObjectFactory.prototype.inputField = function (x, y, inputOptions, group) {
                if (group === undefined) {
                    group = this.world;
                }
                var nineSliceObject = new PhaserInput.InputField(this.game, x, y, inputOptions);
                return group.add(nineSliceObject);
            };
            Phaser.GameObjectCreator.prototype.inputField = function (x, y, inputOptions) {
                return new PhaserInput.InputField(this.game, x, y, inputOptions);
            };
        };
        return Plugin;
    }(Phaser.Plugin));
    Plugin.Zoomed = false;
    Plugin.KeyboardOpen = false;
    Plugin.onKeyboardOpen = new Phaser.Signal();
    Plugin.onKeyboardClose = new Phaser.Signal();
    PhaserInput.Plugin = Plugin;
})(PhaserInput || (PhaserInput = {}));
//# sourceMappingURL=phaser-input.js.map