import React from 'react'
import ReactDOM from 'react-dom'

import { Grid, Row, Col } from 'react-flexbox-grid';

import Slider from 'react-rangeslider'
import 'react-rangeslider/lib/index.css'


class FloatPercentSlider extends React.Component {
    constructor (props, context) {
        super(props, context);
        this.handleChange = this.handleChange.bind(this);
    }

    handleChange(newval) {
        this.props.propagateChange(newval);
    }

    render () {
        const value = this.props.value;
        return (
          <div className='slider'>
            <Slider
              min={0}
              max={100}
              step={0.25}
              value={value}
              onChange={this.handleChange}
            />
            <div className='value'>{value}%</div>
          </div>
        )
    }
}

class DwellSlider extends React.Component {
    constructor (props, context) {
        super(props, context);
        this.handleChange = this.handleChange.bind(this);
    }

    handleChange(newval) {
        this.props.propagateChange(newval);
    }

    render () {
        const value = this.props.value;
        return (
          <div className='slider'>
            <Slider
              min={0}
              max={900}
              step={0.25}
              value={value}
              onChange={this.handleChange}
            />
            <div className='value'>{value}s</div>
          </div>
        )
    }
}


class Motor extends React.Component {
    constructor (props, context) {
        super(props, context);
        this.handleSpeedChange = this.handleSpeedChange.bind(this);
        this.handlePositionChange = this.handlePositionChange.bind(this);
    }

    handlePositionChange(newval) {
        if (this.props.propagateChange) {
            this.props.propagateChange(this.props.id, newval, 0);
        }
    }

    handleSpeedChange(newval) {
        if (this.props.propagateChange) {
            this.props.propagateChange(this.props.id, newval, 1);
        }
    }

    render () {
        return(
            <Row className='motor' >
                <Col md={2}>
                    <h2>{this.props.id}</h2>
                </Col>
                <Col className='position' md={4}>
                    <h3>Position</h3>
                    <FloatPercentSlider value={this.props.position} propagateChange={this.handlePositionChange} />
                </Col>
                <Col className='speed' md={4}>
                    <h3>Speed</h3>
                    <FloatPercentSlider value={this.props.speed} propagateChange={this.handleSpeedChange} />
                </Col>
            </Row>
        )
    }
}

class SequenceStep extends React.Component {
    constructor (props, context) {
        super(props, context);
        this.handleMotorChange = this.handleMotorChange.bind(this);
        this.handleDwellChange = this.handleDwellChange.bind(this);
    }

    handleMotorChange(motorid, newval, validx) {
        if (this.props.propagateMotorChange) {
            this.props.propagateMotorChange(this.props.stepno, motorid, newval, validx);
        }
    }

    handleDwellChange(newval) {
        if (this.props.propagateDwellChange) {
            this.props.propagateDwellChange(this.props.stepno, newval);
        }
    }

    render() {
        return (
            <Row className='sequencestep'>
                <Col md={12}>
                    <Row>
                        <Col md={4}><Motor id="Motor1" speed={this.props.m1speed} position={this.props.m1position} propagateChange={this.handleMotorChange} /></Col>
                        <Col md={4}><Motor id="Motor2" speed={this.props.m2speed} position={this.props.m2position} propagateChange={this.handleMotorChange} /></Col>
                        <Col md={4}><Motor id="Motor3" speed={this.props.m3speed} position={this.props.m3position} propagateChange={this.handleMotorChange} /></Col>
                    </Row>
                    <Row>
                        <Col md={6}>
                            <h3>Dwell</h3>
                            <DwellSlider value={this.props.dwell} propagateChange={this.handleDwellChange} />
                        </Col>
                    </Row>
                </Col>
            </Row>
        )
    }
}

class Main extends React.Component {
    constructor (props, context) {
        super(props, context);
        this.state = {
            sequence: {
                loop: 1,
                start_with_home: 1,
                steps: []
            }
        }
        this.handleMotorChange = this.handleMotorChange.bind(this);
        this.handleDwellChange = this.handleDwellChange.bind(this);
        this.render_row = this.render_row.bind(this);
    }

    handleMotorChange(stepno, motorid, newval, validx) {
        var seq_mod = this.state.sequence;
        seq_mod.steps[stepno].motors[motorid][validx] = newval;
        this.setState({ sequence: seq_mod})
    }

    handleDwellChange(stepno, newval) {
        var seq_mod = this.state.sequence;
        seq_mod.steps[stepno].dwell = newval;
        this.setState({ sequence: seq_mod})
    }

    componentDidMount(){
        var me = this;
        var url = function(s) {
            var l = window.location;
            return ((l.protocol === "https:") ? "wss://" : "ws://") + l.host + s;
        };
        this.seqws = new WebSocket(url('/ws'));
        this.seqws.onopen = function(event) {
            console.log(event);
            event.currentTarget.send(JSON.stringify({ cmd: "get_sequence" }))
        };
        this.seqws.onmessage = function(event) {
            console.log(event.data)
            var msg = JSON.parse(event.data);
            switch(msg.type) {
                case "sequence":
                    me.setState({ sequence: msg.sequence})
                    break;
            }
        }
    }

    componentWillUnmount(){
        this.seqws.close()
    }

    save_sequence(){
        this.seqws.send(JSON.stringify({
            cmd: "save_sequence" ,
            sequence: this.state.sequence
        }))
    }

    add_row(){
        var seq_mod = this.state.sequence;
        seq_mod.steps.push({
            dwell: 0,
            motors: {
                Motor1: [0,0],
                Motor2: [0,0],
                Motor3: [0,0]
            }
        });
        this.setState({ sequence: seq_mod})
    }

    remove_last_row(){
        var seq_mod = this.state.sequence;
        seq_mod.steps.splice(-1)
        this.setState({ sequence: seq_mod})
    }


    render_row(row, index){
        return(
            <Row key={index.toString()}>
                <Col md={11}>
                    <SequenceStep
                        stepno={index}
                        dwell={row.dwell}
                        m1speed={row.motors.Motor1[1]} m1position={row.motors.Motor1[0]}
                        m2speed={row.motors.Motor2[1]} m2position={row.motors.Motor2[0]}
                        m3speed={row.motors.Motor3[1]} m3position={row.motors.Motor3[0]}
                        propagateDwellChange={this.handleDwellChange}
                        propagateMotorChange={this.handleMotorChange}
                    />
                </Col>
            </Row>
        )
    }

    render_rows(){
        return this.state.sequence.steps.map(this.render_row)
    }

    render() {
        return (
            <Grid fluid>
                {this.render_rows()}
                <Row>
                    <Col md={2}><button onClick={(_) => {this.add_row()}}>Add row</button></Col>
                    <Col md={2}><button onClick={(_) => {this.remove_last_row()}}>Remove row</button></Col>
                    <Col md={2}><button onClick={(_) => {this.save_sequence()}}>Save and restart</button></Col>
                </Row>
            </Grid>
        )
    }
}



const app = document.getElementById('app')
ReactDOM.render(<Main />, app)
