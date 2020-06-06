import Phaser from "phaser";

let PG = {
    music: null,
    playerInfo: {},
    orientated: false
};

class BootScene extends Phaser.Scene {

    constructor() {
        super('BootScene')
    }

    preload() {
        this.load.audio('music_game', 'assets/audio/bg_game.ogg');
        this.load.audio('music_room', 'assets/audio/bg_room.mp3');
        this.load.audio('music_deal', 'assets/audio/deal.mp3');
        this.load.audio('music_win',  'assets/audio/end_win.mp3');
        this.load.audio('music_lose', 'assets/audio/end_lose.mp3');
        this.load.audio('f_score_0', 'assets/audio/f_score_0.mp3');
        this.load.audio('f_score_1', 'assets/audio/f_score_1.mp3');
        this.load.audio('f_score_2', 'assets/audio/f_score_2.mp3');
        this.load.audio('f_score_3', 'assets/audio/f_score_3.mp3');
        this.load.multiatlas('ui', 'assets/ui.json', 'assets');
        this.load.image('bg', 'assets/bg.png');
        this.load.spritesheet('poker', 'assets/poker.png', {
            frameWidth: 90,
            frameHeight: 120
        });
        this.load.json('rule', 'assets/rule.json');
    }

    create() {
        // this.scene.start('MenuScene');
        this.scene.start('GameScene');
        // let music = this.sound.add('music_room');
        // music.loop = true;
        // music.play();
    }
}

class MenuScene extends Phaser.Scene {

    constructor() {
        super('MenuScene')
    }

    create() {
        this.backgroundColor = '#182d3b';
        let bg = this.add.sprite(this.game.config.width / 2, 0, 'bg');
        bg.setOrigin(0.5, 0);

        const self = this;
        let aiRoom = this.add.sprite(this.game.config.width / 2, this.game.config.height / 4, 'ui', 'quick.png');
        aiRoom.setInteractive().on('pointerup', () => this.gotoAiRoom());

        let humanRoom = this.add.sprite(this.game.config.width / 2, this.game.config.height / 2, 'ui', 'start.png');
        humanRoom.setInteractive().on('pointerup', () => this.gotoAiRoom());

        let setting = this.add.sprite(this.game.config.width / 2, this.game.config.height * 3 / 4, 'ui', 'setting.png');
        setting.setOrigin(0.5);

        let style = {fontSize: "28px", backgroundColor: "#f0f0f0", color: "#333", align: "left"};
        let text = this.add.text(15, 10, "欢迎回来 " + PG.playerInfo.username, style);
        text.setOrigin(0, 0);
    }

    gotoAiRoom() {
        this.scene.start('GameScene');
        // this.music.stop();
    }

    gotoRoom() {
        this.scene.start('GameScene');
    }

    gotoSetting() {
        let style = {font: "22px Arial", fill: "#fff", align: "center"};
        let text = this.add.text(0, 0, "hei hei hei hei", style);
        let tween = this.add.tween(text).to({x: 600, y: 450}, 2000, "Linear", true);
        tween.onComplete.add(Phaser.Text.prototype.destroy, text);
    }
}

export {BootScene, MenuScene}