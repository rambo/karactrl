import React from 'react'
import ReactDOM from 'react-dom'

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

class Main extends React.Component {
  render() {
      return (
          <div>
              <h1>Hello World</h1>
              <FloatPercentSlider />
          </div>
      )
  }
}



const app = document.getElementById('app')
ReactDOM.render(<Main />, app)
