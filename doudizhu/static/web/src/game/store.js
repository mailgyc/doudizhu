import {combineReducers, createStore} from "redux";
import initSubscriber from 'redux-subscriber'

export const SER_LIST_TABLE = 'ser_list_table';
export const SER_CREATE_TABLE = 'ser_create_table';
export const SER_JOIN_TABLE = 'ser_join_table';

export const SER_DEAL_POKER = 'ser_deal_poker';
export const SER_CALL_SCORE = 'ser_call_score';
export const SER_HOLE_POKER = 'ser_hole_poker';
export const SER_SHOT_POKER = 'ser_shot_poker';
export const SER_GAME_OVER = 'ser_game_over';

export const SER_CHAT = 'ser_chat';

const table = function (state, action) {
    if (typeof state === 'undefined') {
        state = {
            list: [],
            tid: -1,
        };
    }
    switch (action.type) {
        case SER_LIST_TABLE:
            return {...state, list: action.tables};
        case SER_JOIN_TABLE:
            return {...state, tid: action.tid};
        default:
            return state;
    }
};

const players = function (state, action) {
    if (typeof state === 'undefined') {
        const playerData = {
            uid: -1,
            face: 1,
            name: '等待玩家加入',
            icon: 'icon_default.png',
            say: '',
        };
        state = {
            p0: playerData,
            p1: {...playerData, face: -1},
            p2: {...playerData, face: 1},
        }
    }
    switch (action.type) {
        case SER_JOIN_TABLE:
            return state.map((player, index) => {
                if (action.seat === index) {
                    return action.player
                }
                return player
            });
        case SER_CHAT:
            return state.map((player, index) => {
                if (action.seat === index) {
                    return {...action.player, say: action.say};
                }
                return player;
            });
        default:
            return state;
    }
};

const pokerInHand = function (state, action) {
    if (typeof state === 'undefined') {
        state = [[], [], []];
        for (let i = 0; i < 17; i++) {
            state[0].push(i);
            state[1].push(i + 17);
            state[2].push(i + 17 * 2);
        }
    }
    switch (action.type) {
        case SER_DEAL_POKER:
            console.log('store.pokerInHand SER_DEAL_POKER');
            // return state.map((pokerInHand, index) => {
            //     if (action.seat === index) {
            //         return action.pokers
            //     }
            //     return pokerInHand
            // });
            return state;
        case SER_CALL_SCORE:
            return state + action.pokers;

        case SER_SHOT_POKER:
            return state.map((pokerInHand, index) => {
                if (action.seat == index) {
                    return pokerInHand.filter(poker => action.pokers.indexOf(poker) !== -1)
                }
                return pokerInHand
            });
        default:
            return state;
    }
};

const pokers = function (state, action) {
    if (typeof state === 'undefined') {
        state = [];
        for (let i = 1; i <= 54; i++) {
            state.push({'pid': i, frame: 54});
        }
    }
    switch (action.type) {
        case SER_DEAL_POKER:
            console.log('store.pokers SER_DEAL_POKER');
            return state.map((poker, index) => {
                if (index < action.pokers.length) {
                    return {...poker, frame: action.pokers[index]}
                }
                return poker;
            });
        case SER_HOLE_POKER:
            return state.concat(state.slice(0, 51), [
                {'pid': 52, frame: action.pokers[0]},
                {'pid': 53, frame: action.pokers[1]},
                {'pid': 54, frame: action.pokers[2]},
            ]);
        default:
            return state;
    }
};

const store = createStore(combineReducers({
    table,
    players,
    pokerInHand,
    pokers
}));

const subscribe = initSubscriber(store);

export {store, subscribe};


