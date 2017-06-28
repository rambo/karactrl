import React from 'react'
import ReactDOM from 'react-dom'

import { Grid, Row, Col } from 'react-flexbox-grid';

import Slider from 'react-rangeslider'
import 'react-rangeslider/lib/index.css'


class FloatPercentSlider extends React.Component {
  constructor (props, context) {
    super(props, context)
    this.state = {
      value: 0
    }
  }

  render () {
    const { value } = this.state
    return (
      <div className='slider'>
        <Slider
          min={0}
          max={100}
          step={0.25}
          value={value}
          onChange={(newval) => this.setState({value: newval})}
        />
        <div className='value'>{value}%</div>
      </div>
    )
  }
}

class DwellSlider extends React.Component {
  constructor (props, context) {
    super(props, context)
    this.state = {
      value: 0
    }
  }

  render () {
    const { value } = this.state
    return (
      <div className='slider'>
        <Slider
          min={0}
          max={900}
          step={0.25}
          value={value}
          onChange={(newval) => this.setState({value: newval})}
        />
        <div className='value'>{value} seconds</div>
      </div>
    )
  }
}


class Motor extends React.Component {
    render () {
        return(
            <Row className='motor' >
                <Col md={2}>
                    <h2>{this.props.id}</h2>
                </Col>
                <Col className='position' md={4}>
                    <h3>Position</h3>
                    <FloatPercentSlider />
                </Col>
                <Col className='speed' md={4}>
                    <h3>Speed</h3>
                    <FloatPercentSlider />
                </Col>
            </Row>
        )
    }
}

class SequenceStep extends React.Component {
    render() {
        return (
            <Row className='sequencestep'>
                <Col md={12}>
                    <Row>
                        <Col md={4}><Motor id="motor1" /></Col>
                        <Col md={4}><Motor id="motor2" /></Col>
                        <Col md={4}><Motor id="motor3" /></Col>
                    </Row>
                    <Row>
                        <Col md={6}>
                            <h3>Dwell</h3>
                            <DwellSlider />
                        </Col>
                    </Row>
                </Col>
            </Row>
        )
    }
}

class Main extends React.Component {
  render() {
      return (
        <Grid fluid>
            <Row><Col md={12}><SequenceStep /></Col></Row>
            <Row><Col md={12}><SequenceStep /></Col></Row>
        </Grid>

      )
  }
}



const app = document.getElementById('app')
ReactDOM.render(<Main />, app)
