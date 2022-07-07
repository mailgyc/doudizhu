import React from 'react'
import Phaser from "phaser";
import {BootScene, MenuScene} from "./boot"
import GameScene from "./game"


class Game extends React.Component {

    constructor(props) {
    	super(props);
    }

    render() {
        const config = {
            type: Phaser.AUTO,
            parent: "game",
            width: 480,
            height: 960,
            backgroundColor: 0x66666,
            scene: [BootScene, MenuScene, GameScene],
            scale: {
                parent: 'game',
                mode: Phaser.Scale.FIT,
                width: 480,
                height: 960,
            }
        };

        // eslint-disable-next-line no-unused-vars
        const game = new Phaser.Game(config);
        return (
            <div style={{margin: 'auto'}} id="game"></div>
        )
    }

}

export default Game;
